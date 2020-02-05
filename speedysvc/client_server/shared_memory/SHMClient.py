import time
import _thread
from os import getpid
from hybrid_lock import CREATE_NEW_OVERWRITE
from speedysvc.serialisation.RawSerialisation import RawSerialisation
from speedysvc.rpc.shared_memory.SHMBase import SHMBase
from speedysvc.rpc.shared_memory.shared_params import \
    PENDING, INVALID, SERVER, CLIENT
from speedysvc.ipc.JSONMMapList import JSONMMapList
from speedysvc.rpc.base_classes.ClientProviderBase import ClientProviderBase


_monitor_started = [False]
_LSHMClients = []
def _monitor_for_dead_conns():
    # Try to recreate connections periodically
    # if they no longer can be established
    while True:
        try:
            for client in _LSHMClients:
                if client.client_lock.get_destroyed() or client.server_lock.get_destroyed():
                    print(f"Locks destroyed - trying to recreate client connection: "
                          f"{client.server_methods.name}:{client.server_methods.port}")
                    client.create_connections()

                try:
                    client.send(b'heartbeat', b'echo_me', timeout=5)
                except:
                    print(f"[SHMClient PID {getpid()}] Heartbeat failed - trying to recreate client connection: "
                          f"{client.server_methods.name}:{client.server_methods.port}")
                    client.create_connections()
        except:
            import traceback
            traceback.print_exc()
        time.sleep(10)


# Make sure more than one lock can't be
# created for a given port per process(!)
_DLocks = {}
_process_wide_lock = _thread.allocate_lock()


class SHMClient(ClientProviderBase, SHMBase):
    def __init__(self, server_methods, port=None, use_spinlock=True):
        self.use_spinlock = use_spinlock
        # Create the shared mmap space/client+server semaphores.

        # Connect to a shared shm/semaphore which stores the
        # current processes which are associated with this service,
        # and add this process' PID.
        ClientProviderBase.__init__(self, server_methods, port)
        self.create_connections()

        if not _monitor_started[0]:
            _monitor_started[0] = True
            _thread.start_new(_monitor_for_dead_conns, ())
        _LSHMClients.append(self)

    def create_connections(self):
        with _process_wide_lock:
            self.pids_array = pids_array = JSONMMapList(self.port, create=False)

            if not self.port in _DLocks:
                _mmap = self.create_pid_mmap(2048, self.port, getpid())
                self.client_lock, self.server_lock = self.get_pid_semaphores(
                    self.port, getpid(), CREATE_NEW_OVERWRITE
                )
                _DLocks[self.port] = [_mmap, self.client_lock, self.server_lock]

                # Make myself known to the server (my PID)
                with pids_array:
                    pids_array.append(getpid())

            else:
                # The way things are currently implemented,
                # can only have a request per client at once.
                # OPEN ISSUE: Should this be changed to allow multiple
                # client connections to servers, so as to work around the GIL???? ============================================================
                _, self.client_lock, self.server_lock = _DLocks[self.port]

    def get_server_methods(self):
        return self.server_methods

    def send(self, cmd, args, timeout=-1):
        if self.client_lock.get_destroyed() or self.server_lock.get_destroyed():
            # If server no longer exists, try to recreate connection
            self.create_connections()

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

        self.client_lock.lock(timeout=timeout, spin=self.use_spinlock)
        try:
            # Next line must be in critical area!
            mmap = _DLocks[self.port][0]

            # Send the result to the server!
            if len(encoded_request) >= (len(mmap)-1):
                #print(f"Client: Recreating memory map to be at "
                #      f"least {len(encoded_request) + 1} bytes")
                old_mmap = mmap
                mmap = self.create_pid_mmap(
                    len(encoded_request) + 1, self.port, getpid()
                )
                mmap[0] = old_mmap[0]
                _DLocks[self.port][0] = mmap
                old_mmap[0] = INVALID
                #print(f"Client: New mmap size is {len(mmap)} bytes "
                #      f"for encoded_request length {len(encoded_request)}")

            assert len(mmap) > len(encoded_request), \
                (len(mmap), len(encoded_request))
            mmap[1:1+len(encoded_request)] = encoded_request

            # Wait for the server to begin processing
            mmap[0] = PENDING
            #print("BEFORE SERVER UNLOCK:",
            #      self.server_lock.get_value(),
            #      self.client_lock.get_value())
            self.server_lock.unlock()

            t_from = time.time()
            while mmap[0] == PENDING:
                # TODO: Give up and try to reconnect if this goes on
                #  for too long - in that case, chances are something's
                #  gone wrong on the server end
                # Preferably, this should be done in cython, if I find time to do it.

                # Spin! - should check to make sure this isn't being called too often
                if timeout != -1:
                    if time.time()-t_from > timeout:
                        raise TimeoutError()

            self.server_lock.lock(timeout=-1, spin=self.use_spinlock)  # CHECK ME!!!!
            try:
                # Make sure response state ok,
                # reconnecting to mmap if resized
                while True: # WARNING
                    if mmap[0] == CLIENT:
                        break  # OK

                    elif mmap[0] == INVALID:
                        #print(f"Client: memory map has been marked as invalid")
                        prev_len = len(mmap)
                        mmap = self.connect_to_pid_mmap(self.port, getpid())
                        _DLocks[self.port][0] = mmap

                        # Make sure it actually is larger than the previous one,
                        # so as to reduce the risk of an infinite loop
                        assert len(mmap) > prev_len, \
                            "New memory map should be larger than the previous one!"

                    elif mmap[0] == SERVER:
                        raise Exception("Should never get here!")
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
            self.client_lock.unlock()

        if response_status == b'+':
            return serialiser.loads(response_data)
        elif response_status == b'-':
            raise Exception(response_data)
        else:
            raise Exception("Unknown status response %s" % response_status)
