import time
import _thread
from warnings import warn
from os import getpid
from speedysvc.serialisation.RawSerialisation import RawSerialisation
from speedysvc.client_server.shared_memory.SHMBase import SHMBase
from speedysvc.client_server.shared_memory.shared_params import \
    PENDING, INVALID, SERVER, CLIENT
from speedysvc.client_server.shared_memory.SHMResourceManager import SHMResourceManager
from speedysvc.client_server.base_classes.ClientProviderBase import ClientProviderBase


_qid_lock = _thread.allocate_lock()
_DQIds = {}


def new_qid(port):
    # The "q" in qid doesn't stand for anything
    # it just means it's a "sub"-id within a p(rocess)id
    with _qid_lock:
        if not port in _DQIds:
            _DQIds[port] = 0
        _DQIds[port] += 1
        return _DQIds[port]


class ResendError(Exception):
    pass


class SHMClient(ClientProviderBase, SHMBase):
    def __init__(self, server_methods, port=None, use_spinlock=True):
        self.pid = getpid()
        self.use_spinlock = use_spinlock
        # Create the shared mmap space/client+server semaphores.

        # Connect to a shared shm/semaphore which stores the
        # current processes which are associated with this service,
        # and add this process' PID.
        ClientProviderBase.__init__(self, server_methods, port)
        assert not hasattr(self, 'qid')
        self.qid = new_qid(self.port)
        self.resource_manager = SHMResourceManager(
            self.port, server_methods.__dict__.get('name')
        )
        # (Note the pid/qid of this connection is registered here)
        self.mmap, self.client_lock, self.server_lock = \
            self.resource_manager.create_client_resources(getpid(), self.qid)

    def __del__(self):
        """
        Clean up resources and tell server
        workers this qid no longer exists
        """
        self.resource_manager.unlink_client_resources(getpid(), self.qid)

    def get_server_methods(self):
        return self.server_methods

    def send(self, cmd, args, timeout=-1):
        num_times = 0
        while True:
            try:
                return self._send(cmd, args, timeout)
            except ResendError:
                if num_times > 20:
                    raise ResendError(
                        f"Client [pid {getpid()}:qid {self.qid}]: "
                        "Resent too many times!"
                    )
                num_times += 1
                continue

    def _send(self, cmd, args, timeout=-1):
        if isinstance(cmd, bytes):
            # cmd -> a bytes object, most likely heartbeat or shutdown
            serialiser = RawSerialisation
        else:
            # cmd -> a function in the ServerMethods subclass
            serialiser = cmd.serialiser
            cmd = cmd.__name__.encode('ascii')

        # Encode the request command/arguments
        # (I've put the encoding/decoding outside the critical area,
        #  so as to potentially allow for more remote commands from
        #  different threads)
        args = serialiser.dumps(args)
        encoded_request = self.request_serialiser.pack(
            len(cmd), len(args)
        ) + cmd + args

        self.client_lock.lock(
            timeout=timeout,
            spin=int(self.use_spinlock)
        )

        try:
            # Next line must be in critical area!
            mmap = self.mmap

            # Send the result to the server!
            if len(encoded_request) >= len(mmap)-1:
                mmap = self.mmap = self.__resize_mmap(mmap, encoded_request)

            assert len(mmap) > len(encoded_request), \
                (len(mmap), len(encoded_request))
            mmap[1:1+len(encoded_request)] = encoded_request

            # Wait for the server to begin processing
            mmap[0] = PENDING
            try:
                self.server_lock.unlock()
            except SystemError:
                # Server has probably crashed
                pass

            checked_server_exists = False
            t_from = time.time()
            while mmap[0] == PENDING:
                # Give up and try to reconnect if this goes on
                # for too long - in that case, chances are something's
                # gone wrong on the server end
                #
                # Preferably, this should be done in cython, if I find time to do it.

                # Spin! - should check to make sure this isn't being called too often
                if timeout != -1:
                    if time.time()-t_from > timeout:
                        raise TimeoutError()

                # Prevent spinning for no reason
                if time.time()-t_from > 0.1:
                    if not checked_server_exists:
                        checked_server_exists = True

                        self.resource_manager.check_for_missing_pids()
                        if not self.resource_manager.get_server_pids():
                            warn(
                                f"Client [pid {getpid()}:qid {self.qid}]: "
                                f"Could not find worker processes for service "
                                f"{self.server_methods.name} - "
                                f"it probably needs to be restarted!"
                            )
                    time.sleep(0.01)

            self.server_lock.lock(
                timeout=-1,
                spin=int(self.use_spinlock)
            )  # CHECK ME!!!!

            try:
                # Make sure response state ok,
                # reconnecting to mmap if resized
                num_times = 0

                while True: # WARNING
                    if mmap[0] == CLIENT:
                        break  # OK

                    elif mmap[0] == INVALID:
                        mmap = self.mmap = self.__reconnect_to_mmap(mmap)
                        assert num_times < 1000, "Shouldn't get here!"
                        num_times += 1

                    elif mmap[0] == SERVER or mmap[0] == PENDING:
                        warn(f"Client [pid {getpid()}:qid {self.qid}]: "
                             f"Lock was released, but still belonged "
                             f"to a server worker - the worker likely has crashed. "
                             f"Resending request to hopefully allow another server "
                             f"pid to handle!")
                        try:
                            self.server_lock.unlock()
                        except:
                            pass
                        raise ResendError()
                    else:
                        raise Exception("Unknown state: %s" % mmap[0])

                # Decode the result!
                response_status, data_size = self.response_serialiser.unpack(
                    mmap[1:1+self.response_serialiser.size]
                )
                response_data = mmap[
                    1+self.response_serialiser.size:
                    1+self.response_serialiser.size+data_size
                ]
            finally:
                pass
        finally:
            try:
                self.client_lock.unlock()
            except:
                # Currently, this method prints error information using perror
                # but this should be replaced with a less blanket handler ===============================================
                pass  # WARNING!

        if response_status == b'+':
            return serialiser.loads(response_data)
        elif response_status == b'-':
            self._handle_exception(response_data)
        else:
            raise Exception("Unknown status response %s" % response_status)

    def __resize_mmap(self, mmap, encoded_request):
        """

        :param mmap:
        :param encoded_request:
        :return:
        """
        #print(f"[pid {getpid()}:qid {self.qid}] "
        #      f"Client: Recreating memory map to be at "
        #      f"least {len(encoded_request)} bytes")

        old_mmap = mmap
        assert self.pid == getpid()
        mmap = self.resource_manager.create_pid_mmap(
            min_size=len(encoded_request) * 2,
            pid=getpid(),
            qid=self.qid
        )

        # Assign the new mmap
        assert len(mmap) > len(old_mmap), (len(old_mmap), len(mmap))
        mmap[0] = old_mmap[0]
        assert mmap[0] != INVALID

        # Make the old one invalid
        old_mmap[0] = INVALID
        old_mmap.close()
        #print(f"Client: New mmap size is {len(mmap)} bytes "
        #      f"for encoded_request length {len(encoded_request)}")
        return mmap

    def __reconnect_to_mmap(self, mmap):
        """

        :param mmap:
        :return:
        """
        #print(f"Client: memory map has been marked as invalid")
        prev_len = len(mmap)
        mmap.close()

        # Make sure that fork() hasn't caused PIDs to
        # get out of sync (if fork() is being used)!
        assert self.pid == getpid()
        mmap = self.resource_manager.connect_to_pid_mmap(
            pid=getpid(),
            qid=self.qid
        )

        # Make sure it actually is larger than the previous one,
        # so as to reduce the risk of an infinite loop
        assert len(mmap) > prev_len, \
            f"[pid {getpid()}:qid {self.qid}] " \
            f"New memory map should be larger than the previous one: " \
            f"{len(mmap)} !> {prev_len}"
        return mmap
