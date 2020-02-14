import time
import traceback
from os import getpid
from _thread import start_new_thread
from speedysvc.client_server.base_classes.ServerProviderBase import ServerProviderBase
from speedysvc.serialisation.RawSerialisation import RawSerialisation
from speedysvc.client_server.shared_memory.SHMBase import SHMBase
from speedysvc.client_server.shared_memory.shared_params import \
    PENDING, INVALID, SERVER, CLIENT
from speedysvc.client_server.shared_memory.SHMResourceManager import \
    SHMResourceManager
from hybrid_lock import SemaphoreDestroyedException


_monitor_pids_started = [False]
_LSHMServers = []
def _monitor_pids():
    """
    Monitor PIDs for all SHMServers in a
    single thread to minimize resources
    """
    while True:
        if not _LSHMServers:
            _monitor_pids_started[0] = False
            return

        for shm_server in _LSHMServers[:]:
            try:
                if shm_server.shut_me_down:
                    _LSHMServers.remove(shm_server)
                else:
                    shm_server.monitor_pids()
            except:
                import traceback
                traceback.print_exc()

        time.sleep(0.5)


class SHMServer(SHMBase, ServerProviderBase):
    def __init__(self, server_methods, use_spinlock=True):
        # NOTE: init_resources should only be called if creating from scratch -
        # if connecting to an existing socket, init_resources should be False!
        ServerProviderBase.__call__(self, server_methods)

        print(f'{server_methods.name}:{server_methods.port}:'
              f'Starting new SHMServer on port:',
              server_methods.port)

        self.port = server_methods.port
        self.shut_me_down = False
        self.shutdown_ok = False
        self.use_spinlock = use_spinlock

        """
        TODO: Create or connect to a shared shm/semaphore which stores the
         current processes which are associated with this service.
        """
        self.SPIDThreads = set()
        self.resource_manager = SHMResourceManager(
            server_methods.port, server_methods.name
        )
        self.resource_manager.check_for_missing_pids()
        self.resource_manager.add_server_pid(getpid())

        _LSHMServers.append(self)
        if not _monitor_pids_started[0]:
            _monitor_pids_started[0] = True
            start_new_thread(_monitor_pids, ())

    def shutdown(self):
        self.shut_me_down = True

        while True:
            try:
                while not self.shutdown_ok:
                    time.sleep(0.05)
                    continue
                break
            except KeyboardInterrupt:
                pass  # HACK!

        # Signify to future MultiProcessManager's
        # they don't need to clean me up
        self.resource_manager.del_server_pid(getpid())

    def monitor_pids(self):
        """
        Monitor the shared shm information about the service periodically,
        starting a new thread for new client PIDs/removing client PIDs which
        don't exist any more, as needed.

        If the client PID no longer exists, also clean up its resources,
        as needed.
        """
        SCreated, SExited = \
            self.resource_manager.get_created_exited_client_pids(
                self.SPIDThreads
            )
        #if SCreated or SExited:
        #    print(f"{self.name}:{self.port}[{self.SPIDThreads}] SCREATED: {SCreated} SEXITED: {SExited}")
        #else:
        #    print(self.SPIDThreads, self.resource_manager.get_client_pids())

        for pid, qid in SCreated:
            # Add newly created client connections
            self.SPIDThreads.add((pid, qid))
            start_new_thread(self.worker_thread_fn, (pid, qid))

        for pid, qid in SExited:
            # Remove connections to clients that no longer exist
            try:
                self.SPIDThreads.remove((pid, qid))
            except KeyError:
                pass

    def worker_thread_fn(self, pid, qid):
        """
        Connect to the shared mmap space/client+server semaphores.
        Continuously poll for commands, responding as needed.
        """
        mmap, client_lock, server_lock = \
            self.resource_manager.open_existing_client_resources(
                pid, qid
            )
        print(f"SHMServer {self.name} started new worker "
              f"thread for pid {pid} subid {qid}")
        do_spin = True

        while True:
            if not (pid, qid) in self.SPIDThreads:
                # PID no longer exists, so don't continue to loop
                return
            elif self.shut_me_down:
                try:
                    self.SPIDThreads.remove((pid, qid))
                except KeyError:
                    pass

                self.shutdown_ok = not len(self.SPIDThreads)
                print(f"Signal to shutdown SHMServer {self.name} "
                      f"in worker thread for pid {pid} subid {qid} caught: "
                      f"returning ({len(self.SPIDThreads)} remaining)")
                return

            try:
                do_spin, mmap = self.handle_command(
                    mmap, server_lock, pid, qid, do_spin
                )
            except SemaphoreDestroyedException:
                # In this case, the lock was likely destroyed by the client
                # and should propagate the error, rather than forever logging
                print(f"Lock for service {self.name} "
                      f"in worker thread for pid {pid} subid {qid} was destroyed: "
                      f"returning ({len(self.SPIDThreads)} remaining)")
                return
            except:
                #import traceback
                #traceback.print_exc()
                # There's error handling for calls themselves, so may be an
                # AssertionError.
                raise

    def handle_command(self, mmap, server_lock, pid, qid, do_spin):
        try:
            server_lock.lock(
                timeout=4,
                spin=int(do_spin and self.use_spinlock)
            )
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
                    #print(f"Server: memory map has been marked as invalid")
                    prev_len = len(mmap)
                    mmap = self.resource_manager.connect_to_pid_mmap(pid, qid)

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

            # Measure for complete time it takes from
            # getting/putting back to the shm block
            # for benchmarking
            t_from = time.time()
            fn = None

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
                # Output to stderr log for the service
                traceback.print_exc()

                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                result = b'-' + repr(exc).encode('utf-8')
                encoded = self.response_serialiser.pack(
                    b'-', len(result)
                ) + result

            # Resize the mmap as needed
            if len(encoded) >= len(mmap)-1:
                #print(f"Server: Recreating memory map to be at "
                #      f"least {len(encoded) + 1} bytes")
                old_mmap = mmap
                mmap = self.resource_manager.create_pid_mmap(
                    min_size=len(encoded)+1,
                    pid=pid,
                    qid=qid
                )
                mmap[0] = old_mmap[0]
                old_mmap[0] = INVALID

            # Set the result, and end the call
            mmap[1:1+len(encoded)] = encoded
            mmap[0] = CLIENT

            # Add to some variables for basic benchmarking
            if hasattr(fn, 'metadata'):
                fn.metadata['num_calls'] += 1
                fn.metadata['total_time'] += time.time() - t_from

        finally:
            server_lock.unlock()
        return do_spin, mmap
