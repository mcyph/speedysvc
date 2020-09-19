import time
import atexit
import _thread
from warnings import warn
from os import getpid
from speedysvc.serialisation.RawSerialisation import RawSerialisation
from speedysvc.client_server.shared_memory.SHMBase import SHMBase
from speedysvc.client_server.shared_memory.shared_params import INVALID, SERVER, CLIENT
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


def debug(*s):
    if False:
        print(*s)


class SHMClient(ClientProviderBase, SHMBase):
    def __init__(self, server_methods, port=None, use_spinlock=True):
        self.pid = getpid()
        self.use_spinlock = use_spinlock
        self._in_process_lock = _thread.allocate_lock()

        # Create the shared mmap space/client+server semaphores.
        #
        # Connect to a shared shm/semaphore which stores the
        # current processes which are associated with this service,
        # and add this process' PID.
        ClientProviderBase.__init__(self, server_methods, port)
        assert not hasattr(self, 'qid')
        self.qid = new_qid(self.port)
        self.resource_manager = SHMResourceManager(self.port, server_methods.__dict__.get('name'))

        # (Note the pid/qid of this connection is registered here)
        self.mmap, self.lock = self.resource_manager.create_resources(getpid(), self.qid)
        self.lock.lock()
        self.cleaned_up = False

        # Add a handler for when the program is exiting to reduce the probability of
        # resources being left over when __del__ isn't called in time
        atexit.register(self.__del__)

    def __del__(self):
        """
        Clean up resources and tell server
        workers this qid no longer exists
        """
        self.resource_manager.unlink_resources(getpid(), self.qid)

    def get_server_methods(self):
        return self.server_methods

    def send(self, cmd, args, timeout=-1):
        with self._in_process_lock:
            num_times = 0
            while True:
                try:
                    return self._send(cmd, args, timeout)
                except ResendError:
                    if num_times > 20:
                        raise ResendError(
                            f"Client [pid {getpid()}:qid {self.qid}]: Resent too many times!"
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
        encoded_request = \
            self.request_serialiser.pack(len(cmd), len(args)) + cmd + args

        # Next line must be in critical area!
        mmap = self.mmap

        if mmap[0] == SERVER:
            raise Exception()

        # Send the result to the server!
        if len(encoded_request) >= len(mmap)-1:
            mmap = self.mmap = self.__resize_mmap(mmap, encoded_request)

        assert len(mmap) > len(encoded_request), (len(mmap), len(encoded_request))
        mmap[1:1+len(encoded_request)] = encoded_request

        # Wait for the server to begin processing
        mmap[0] = SERVER

        # Release the lock for the server
        self.lock.unlock()

        # Make sure response state ok,
        # reconnecting to mmap if resized
        num_times = 0

        while True:
            if not num_times:
                #debug("LOCKING CLIENT LOCK <- SERVER!", mmap[0] == SERVER, mmap[0] == CLIENT, cmd)
                self.lock.lock(timeout=-1, spin=int(self.use_spinlock))
                #debug("LOCKED!")

            if mmap[0] == CLIENT:
                # OK
                break
            elif mmap[0] == INVALID:
                # Need to reconnect
                mmap = self.mmap = self.__reconnect_to_mmap(mmap)
                assert num_times < 1000, "Shouldn't get here!"
                num_times += 1
            elif mmap[0] == SERVER:
                # Server hasn't caught the request yet!
                self.lock.unlock()
                continue
            else:
                raise Exception("Unknown state: %s" % chr(mmap[0]))

        # Next line must be in critical area!
        mmap = self.mmap
        size = self.response_serialiser.size

        # Decode the result!
        response_status, data_size = self.response_serialiser.unpack(mmap[1:1+size])
        response_data = mmap[1+size : 1+size+data_size]

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
        debug(f"[pid {getpid()}:qid {self.qid}] "
              f"Client: Recreating memory map to be at "
              f"least {len(encoded_request)} bytes")

        old_mmap = mmap
        assert self.pid == getpid()
        mmap = self.resource_manager.create_pid_mmap(
            min_size=len(encoded_request)*2, pid=getpid(), qid=self.qid
        )

        # Assign the new mmap
        assert len(mmap) > len(old_mmap), (len(old_mmap), len(mmap))
        mmap[0] = old_mmap[0]
        assert mmap[0] != INVALID

        # Make the old one invalid
        old_mmap[0] = INVALID
        old_mmap.close()
        debug(f"Client: New mmap size is {len(mmap)} bytes "
              f"for encoded_request length {len(encoded_request)}")
        return mmap

    def __reconnect_to_mmap(self, mmap):
        """

        :param mmap:
        :return:
        """
        debug(f"Client: memory map has been marked as invalid")
        prev_len = len(mmap)
        mmap.close()

        # Make sure that fork() hasn't caused PIDs to
        # get out of sync (if fork() is being used)!
        assert self.pid == getpid()
        mmap = self.resource_manager.connect_to_pid_mmap(pid=getpid(), qid=self.qid)

        # Make sure it actually is larger than the previous one,
        # so as to reduce the risk of an infinite loop
        assert len(mmap) > prev_len, \
            f"[pid {getpid()}:qid {self.qid}] " \
            f"New memory map should be larger than the previous one: " \
            f"{len(mmap)} !> {prev_len}"
        return mmap
