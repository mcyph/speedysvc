import time
from _thread import start_new_thread
from shmrpc.rpc.base_classes.ServerProviderBase import ServerProviderBase
from shmrpc.serialisation.RawSerialisation import RawSerialisation
from shmrpc.ipc.JSONMMapList import JSONMMapList
from shmrpc.rpc.shared_memory.SHMBase import SHMBase
from shmrpc.rpc.shared_memory.shared_params import \
    PENDING, INVALID, SERVER, CLIENT
from hybrid_lock import CONNECT_TO_EXISTING


class SHMServer(SHMBase, ServerProviderBase):
    def __init__(self):
        pass

    def __call__(self, server_methods, init_resources=True):
        # TODO!
        print(f"{server_methods.name}:{server_methods.port}: "
              f"SHMServer __call__; init_resources:", init_resources)
        # NOTE: init_resources should only be called if creating from scratch -
        # if connecting to an existing socket, init_resources should be False!
        ServerProviderBase.__call__(self, server_methods)

        print('Starting new SHMServer on port:',
              server_methods.port, init_resources)
        self.port = server_methods.port
        self.shut_me_down = False
        self.shutdown_ok = False

        # Add some default methods: heartbeat to make sure the service
        # is responding to requests; shutdown to cleanly exit.
        self.server_methods.heartbeat = lambda data: data
        self.server_methods.heartbeat.serialiser = RawSerialisation

        """
        TODO: Create or connect to a shared shm/semaphore which stores the
         current processes which are associated with this service.
        """
        self.init_pids_map_array(init_resources)
        start_new_thread(self.monitor_pids, ())
        return self

    def shutdown(self):
        self.shut_me_down = True
        while not self.shutdown_ok:
            time.sleep(0.05)
            continue

    def init_pids_map_array(self, init_resources):
        self.LPIDs = JSONMMapList(
            port=self.port, create=init_resources
        )
        self.SPIDThreads = set()

    def monitor_pids(self):
        """
        Monitor the shared shm information about the service periodically,
        starting a new thread for new client PIDs/removing client PIDs which
        don't exist any more, as needed.

        If the client PID no longer exists, also clean up its resources,
        as needed.
        """
        while True:
            if self.shut_me_down:
                return
            try:
                with self.LPIDs:
                    SPIDs = set()
                    for pid in self.LPIDs:
                        SPIDs.add(pid)
                        if self.shut_me_down:
                            # Don't start any more threads if
                            # a shutdown has been requested!
                            return
                        elif not pid in self.SPIDThreads:
                            self.SPIDThreads.add(pid)
                            start_new_thread(self.main, (pid,))

                    for pid in list(self.SPIDThreads):
                        if not pid in SPIDs:
                            self.SPIDThreads.remove(pid)
            except:
                import traceback
                traceback.print_exc()

            time.sleep(0.5)

    def main(self, pid):
        """
        Connect to the shared mmap space/client+server semaphores.
        Continuously poll for commands, responding as needed.
        """
        client_lock, server_lock = self.get_pid_semaphores(
            self.port, pid, mode=CONNECT_TO_EXISTING
        )
        mmap = self.connect_to_pid_mmap(self.server_methods.port, pid)
        do_spin = True

        while True:
            if not pid in self.SPIDThreads:
                # PID no longer exists, so don't continue to loop
                return
            elif self.shut_me_down:
                self.SPIDThreads.remove(pid)
                self.shutdown_ok = not len(self.SPIDThreads)
                print(f"Signal to shutdown SHMServer {self.name} "
                      f"in worker thread for pid {pid} caught: "
                      f"returning ({len(self.SPIDThreads)} remaining)")
                return

            try:
                do_spin, mmap = self.handle_command(mmap, server_lock, pid, do_spin)
            except:
                import traceback
                traceback.print_exc()

    def handle_command(self, mmap, server_lock, pid, do_spin):
        try:
            server_lock.lock(timeout=1, spin=do_spin)
            do_spin = True
        except TimeoutError:
            # Disable spinning for subsequent tries!
            do_spin = False
            return do_spin, mmap

        try:
            while True: # WARNING
                # Prepare for handling command
                if mmap[0] == PENDING:
                    break # OK
                elif mmap[0] == INVALID:
                    # Size change - re-open the mmap!
                    print(f"Server: memory map has been marked as invalid")
                    prev_len = len(mmap)
                    mmap = self.connect_to_pid_mmap(self.port, pid)

                    # Make sure it actually is larger than the previous one,
                    # so as to reduce the risk of an infinite loop
                    assert len(mmap) > prev_len, \
                        "New memory map should be larger than the previous one!"
                    continue
                elif mmap[0] == CLIENT:
                    # We'll just return here, as we
                    # shouldn't have obtained the lock
                    return False, mmap # Should this not spin??? ========================================
                elif mmap[0] == SERVER:
                    raise Exception("Should never get here!")
                else:
                    raise Exception("Unknown state: %s" % mmap[0])

            # Get the command+parameters
            mmap[0] = SERVER
            cmd_len, args_len = self.request_serialiser.unpack(
                mmap[1:1 + self.request_serialiser.size]
            )
            cmd = mmap[
                1 + self.request_serialiser.size:
                1 + self.request_serialiser.size + cmd_len
            ].decode('ascii')
            args = mmap[
                1 + self.request_serialiser.size + cmd_len:
                1 + self.request_serialiser.size + cmd_len + args_len
            ]

            try:
                # Handle the command
                fn = getattr(self.server_methods, cmd)
                serialiser = fn.serialiser
                if serialiser == RawSerialisation:
                    result = serialiser.dumps(fn(args))
                else:
                    result = serialiser.dumps(fn(*serialiser.loads(args)))

                encoded = self.response_serialiser.pack(
                    b'+', len(result)
                ) + result

            except Exception as exc:
                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                result = b'-' + repr(exc).encode('utf-8')
                encoded = self.response_serialiser.pack(
                    b'-', len(result)
                ) + result

            # Resize the mmap as needed
            if len(encoded) >= len(mmap)-1:
                print(f"Server: Recreating memory map to be at "
                      f"least {len(encoded) + 1} bytes")
                old_mmap = mmap
                mmap = self.create_pid_mmap(
                    min_size=len(encoded)+1, port=self.port, pid=pid
                )
                mmap[0] = old_mmap[0]
                old_mmap[0] = INVALID

            # Set the result, and end the call
            mmap[1:1+len(encoded)] = encoded
            mmap[0] = CLIENT

        finally:
            server_lock.unlock()
        return do_spin, mmap
