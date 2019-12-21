import time
from os import getpid
from _thread import start_new_thread
from network_tools.rpc.base_classes.ServerProviderBase import ServerProviderBase
from network_tools.serialisation.RawSerialisation import RawSerialisation
from network_tools.rpc.shared_memory.JSONMMapArray import JSONMMapArray
from network_tools.rpc.shared_memory.SHMBase import SHMBase
from network_tools.rpc.shared_memory.shared_params import \
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

        # Add some default methods: heartbeat to make sure the service
        # is responding to requests; shutdown to cleanly exit.
        self.server_methods.heartbeat = lambda data: data
        self.server_methods.heartbeat.serialiser = RawSerialisation
        def shutdown(data):
            pass  # TODO!
        self.server_methods.shutdown = shutdown

        """
        TODO: Create or connect to a shared shm/semaphore which stores the
         current processes which are associated with this service.
        """
        self.init_pids_map_array(init_resources)
        start_new_thread(self.monitor_pids, ())
        return self

    def shutdown(self):
        self.shut_me_down = True
        t_from = time.time()
        while not self.shutdown_ok:
            time.sleep(0.05)
            if time.time() - t_from > 5:
                print(f"Trying to send shutdown command to SHMServer")
                # kill_thread(self.serve_thread_loop)
                from network_tools.rpc.shared_memory.SHMClient import SHMClient
                client = SHMClient(self.server_methods)
                shutdown_ok = False
                for x in range(10000):
                    xx = client.send(b'shutdown', str(getpid()).encode('ascii'))
                    print("SHUTDOWN RESPONSE:", xx)
                    if xx == b'ok':
                        print(f"Thread shutdown OK pid [{getpid()}]")
                        shutdown_ok = True
                        break

                if not shutdown_ok:
                    print(f"SHUTDOWN NOT OK!!! pid [{getpid()}]")
                    time.sleep(1)
                    raise Exception(f"SHUTDOWN NOT OK!!! pid [{getpid()}]")
                time.sleep(1)
                break

    def init_pids_map_array(self, init_resources):
        self.LPIDs = JSONMMapArray(
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
        # TODO:
        if server_lock.get_value() and mmap[0] == CLIENT:
            # Don't try to take over if the client is going to
            # TODO: Perhaps this should sleep after a certain
            #  amount of time?
            return True, mmap # spin spin spin! - CHECK ME!!!! ===========================================================

        try:
            server_lock.lock(timeout=1, spin=do_spin)
            do_spin = True
        except TimeoutError:
            # Disable spinning for subsequent tries!
            do_spin = False
            return do_spin, mmap

        try:
            for x in range(2):
                # Prepare for handling command
                if mmap[0] == PENDING:
                    break # OK
                elif mmap[0] == INVALID:
                    # Size change - re-open the mmap!
                    print(f"Server: memory map has been marked as invalid")
                    mmap = self.connect_to_pid_mmap(self.port, pid)
                    continue
                elif mmap[0] == CLIENT:
                    # We'll just return here, as we
                    # shouldn't have obtained the lock
                    return do_spin, mmap # Should this not spin??? ========================================
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
            if len(encoded) > len(mmap)-1:
                print(f"Server: Recreating memory map to be at "
                      f"least {len(encoded) + 1} bytes")
                old_mmap = mmap
                mmap = self.create_pid_mmap(
                    min_size=len(encoded)+1, port=self.port, pid=pid
                )
                old_mmap[0] = INVALID

            # Set the result, and end the call
            mmap[1:1+len(encoded)] = encoded
            mmap[0] = CLIENT

        finally:
            server_lock.unlock()
        return do_spin, mmap
