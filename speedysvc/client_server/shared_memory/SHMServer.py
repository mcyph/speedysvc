import sys
import time
import traceback
from os import getpid
from _thread import start_new_thread
from typing import Optional

import psutil

from speedysvc.client_server.shared_memory.SHMBase import SHMBase
from speedysvc.serialisation.RawSerialisation import RawSerialisation
from speedysvc.client_server.base_classes.ServerProviderBase import ServerProviderBase
from speedysvc.client_server.shared_memory.shared_params import INVALID, SERVER, CLIENT
from speedysvc.client_server.shared_memory.SHMResourceManager import SHMResourceManager
from speedysvc.hybrid_lock import NoSuchSemaphoreException, SemaphoreDestroyedException, SemaphoreExistsException
from speedysvc.service_method import FunctionMetaData

_monitor_pids_started = [False]
_shm_servers_list = []


def _monitor_pids():
    """
    Monitor PIDs for all SHMServers in a
    single thread to minimize resources
    """
    while True:
        if not _shm_servers_list:
            _monitor_pids_started[0] = False
            return

        for shm_server in _shm_servers_list[:]:
            try:
                if shm_server.shut_me_down:
                    _shm_servers_list.remove(shm_server)
                else:
                    shm_server.monitor_pids()
            except:
                import traceback
                traceback.print_exc()

        time.sleep(0.5)


def debug(*s):
    if False:
        print(*s)


class SHMServer(SHMBase, ServerProviderBase):
    def __init__(self,
                 server_methods,
                 service_port: int,
                 service_name: str,
                 use_spinlock: bool = True):

        # NOTE: init_resources should only be called if creating from scratch -
        # if connecting to an existing socket, init_resources should be False!
        ServerProviderBase.__init__(self,
                                    server_methods=server_methods,
                                    service_name=service_name,
                                    service_port=service_port)

        self.service_port = service_port
        self.service_name = service_name

        self.shut_me_down = False
        self.shutdown_ok = False
        self.use_spinlock = use_spinlock

        self.pid_threads_set = set()
        self.resource_manager = SHMResourceManager(port=self.service_port,
                                                   name=self.service_name)

    def serve_forever(self):
        self.serve_forever_in_new_thread()
        try:
            while True:
                time.sleep(10)
        except:
            self.shutdown()
            raise

    def serve_forever_in_new_thread(self):
        """
        TODO: Create or connect to a shared shm/semaphore which stores the
              current processes which are associated with this service.
        """
        #debug(f'{self.service_name}:{self.service_port}: Starting new SHMServer on service_port:', self.service_port)

        self.resource_manager.check_for_missing_pids()
        self.resource_manager.add_server_pid(getpid())

        _shm_servers_list.append(self)
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
        created_set, exited_set = self.resource_manager.get_created_exited_client_pids(self.pid_threads_set)
        #if created_set or exited_set:
        #    debug(f"{self.service_name}:{self.service_port}[{self.pid_threads_set}] SCREATED: {created_set} SEXITED: {exited_set}")
        #else:
        #    debug(self.pid_threads_set, self.resource_manager.get_client_pids())

        for pid, qid in created_set:
            # Add newly created client connections
            self.pid_threads_set.add((pid, qid))
            start_new_thread(self.worker_thread_fn, (pid, qid))

        for pid, qid in exited_set:
            # Remove connections to clients that no longer exist
            try:
                self.pid_threads_set.remove((pid, qid))
            except KeyError:
                pass

    def worker_thread_fn(self, pid: int, qid: int):
        """
        Connect to the shared mmap space/client+server semaphores.
        Continuously poll for commands, responding as needed.
        """
        try:
            mmap, lock = self.resource_manager.open_existing_resources(pid, qid)
        except (NoSuchSemaphoreException, FileNotFoundError):
            # Resources might've been destroyed
            # in the meantime by the client?
            #debug("EXISTENTIAL ERROR:", pid, qid)
            return

        #debug(f"SHMServer {self.service_name} started new worker "
        #      f"thread for pid {pid} subid {qid}")
        do_spin = True

        iterators = {}
        current_iterator_id = 0

        while True:
            if not (pid, qid) in self.pid_threads_set:
                # PID no longer exists, so don't continue to loop
                return
            elif self.shut_me_down:
                try:
                    self.pid_threads_set.remove((pid, qid))
                except KeyError:
                    pass

                self.shutdown_ok = not len(self.pid_threads_set)
                #debug(f"Signal to shutdown SHMServer {self.service_name} "
                #      f"in worker thread for pid {pid} subid {qid} caught: "
                #      f"returning ({len(self.pid_threads_set)} remaining)")
                return

            try:
                do_spin, mmap, current_iterator_id = self.handle_command(mmap,
                                                                         lock,
                                                                         iterators,
                                                                         current_iterator_id,
                                                                         pid,
                                                                         qid,
                                                                         do_spin)
            except SemaphoreDestroyedException:
                # In this case, the lock was likely destroyed by the client
                # and should propagate the error, rather than forever logging
                #debug(f"Lock for service {self.service_name} "
                #      f"in worker thread for pid {pid} subid {qid} was destroyed: "
                #      f"returning ({len(self.pid_threads_set)} remaining)")
                return
            except:
                import traceback
                traceback.print_exc()
                # There's error handling for calls themselves, so may be an
                # AssertionError.
                raise

    def handle_command(self,
                       mmap,
                       lock,
                       iterators: dict,
                       current_iterator_id: int,
                       pid: int,
                       qid: int,
                       do_spin: bool):

        #debug("SERVER LOCK:", pid, qid, do_spin)
        try:
            lock.lock(timeout=4,
                      spin=int(do_spin and self.use_spinlock))
            do_spin = True
        except TimeoutError:
            # Disable spinning for subsequent tries!
            do_spin = False
            return do_spin, mmap, current_iterator_id
        #debug("SERVER LOCK OBTAINED:", pid, qid, do_spin, mmap[0] == SERVER, mmap[0] == CLIENT)

        try:
            num_times = 0
            while True:  # WARNING
                # Prepare for handling command
                if mmap[0] == CLIENT:
                    # No command to process!
                    return do_spin, mmap, current_iterator_id
                elif mmap[0] == SERVER:
                    # Command to process sent from client!
                    break
                elif mmap[0] == INVALID:
                    # Size change - re-open the mmap!
                    mmap = self.__reconnect_to_mmap(pid, qid, mmap)
                    assert num_times < 1000, "Shouldn't get here!"
                    num_times += 1
                else:
                    # Connection destroyed? (Windows)
                    raise SemaphoreDestroyedException(f"Service {self.service_name} pid/qid {pid}:"
                                                      f"{qid} unknown state: %s" % mmap[0])

            # Measure for complete time it takes from
            # getting/putting back to the shm block
            # for benchmarking
            t_from = time.time()
            fn = None

            # Get the command+parameters
            size = self.request_serialiser.size
            cmd_len, args_len = self.request_serialiser.unpack(mmap[1:1 + self.request_serialiser.size])
            cmd = mmap[1+size : 1+size+cmd_len].decode('ascii')
            args = mmap[1+size+cmd_len : 1+size+cmd_len+args_len]
            metadata: Optional[FunctionMetaData] = None

            if cmd in ('$iter_next$', '$iter_destroy$'):
                iter_pid, iter_id = args.split(b'_')
                if int(iter_pid) != getpid():
                    # Unlock for the process which does have this iterator ID to process

                    # FIXME: Find a more resource-efficient means of doing the below! =========================================================
                    #if not psutil.pid_exists(int(iter_pid)):
                        # If the pid no longer exists for this iterator, reset the lock state!
                    #    mmap[0] = CLIENT
                    return do_spin, mmap, current_iterator_id

            try:
                if cmd == '$iter_next$':
                    # Continue on from where the iterator left off
                    metadata, iter_ = iterators[args]

                    out = []
                    for x in range(metadata.iterator_page_size):
                        try:
                            item = next(iter_)
                            if metadata.encode_returns:
                                item = metadata.encode_returns(item)
                            out.append(item)
                        except StopIteration:
                            del iterators[args]
                            break

                    result = metadata.return_serialiser.dumps(out)
                    metadata = None  # don't add to stats below

                elif cmd == '$iter_destroy$':
                    del iterators[args]
                    result = b''

                else:
                    # Handle the command
                    fn = getattr(self.server_methods, cmd)
                    metadata = fn.metadata

                    # Deserialise the arguments according to the metadata
                    if metadata.params_serialiser == RawSerialisation:
                        # TODO: Separate into positional, spread, keywords
                        var_positional = (args,)
                        var_keyword = None
                    else:
                        var_positional, var_keyword = metadata.params_serialiser.loads(args)

                    # "Unbox" any parameters as needed
                    if metadata.decode_params:
                        for k, v in metadata.decode_params.items():
                            args[k] = v(args[k])

                    # Serialise the return value according to the metadata and
                    # encode "+" with length to say the call succeeded
                    if metadata.returns_iterator:
                        # Return an id, then stash the iterator for later referring to it
                        iter_id = f'{getpid()}_{current_iterator_id}'.encode('ascii')
                        iterators[iter_id] = metadata, iter(fn(*(var_positional or ()),
                                                               **(var_keyword or {})))  # CHECK THIS!
                        result = iter_id
                        current_iterator_id += 1
                    else:
                        result = fn(*(var_positional or ()), **(var_keyword or {}))
                        if metadata.encode_returns:
                            # Box any return values as needed
                            result = metadata.encode_returns(result)
                        result = metadata.return_serialiser.dumps(result)

                encoded = self.response_serialiser.pack(b'+', len(result)) + result

            except Exception as exc:
                # Output to stderr log for the service
                sys.stderr.write(f"Service {self.service_name} error handling method: {fn}\n")
                traceback.print_exc()

                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                result = b'-' + repr(exc).encode('utf-8')
                encoded = self.response_serialiser.pack(b'-', len(result)) + result

            # Resize the mmap as needed
            if len(encoded) >= len(mmap)-1:
                mmap = self.__resize_mmap(pid, qid, mmap, encoded)

            # Set the result, and end the call
            mmap[1:1+len(encoded)] = encoded
            mmap[0] = CLIENT

            # Add to some variables for basic benchmarking
            if metadata is not None:
                metadata.num_calls += 1
                metadata.total_time += time.time() - t_from

        finally:
            lock.unlock()
        return do_spin, mmap, current_iterator_id

    def __resize_mmap(self,
                      pid: int,
                      qid: int,
                      mmap,
                      encoded: bytes):
        #debug(
        #    f"[pid {pid}:qid {qid}] "
        #    f"Server: Recreating memory map to be at "
        #    f"least {len(encoded) + 1} bytes"
        #)

        old_mmap_len = len(mmap)
        old_mmap_statuscode = mmap[0]

        # Make the old one invalid
        mmap[0] = INVALID
        mmap.close()

        # Assign the new mmap
        mmap = self.resource_manager.create_pid_mmap(min_size=len(encoded) * 2,
                                                     pid=pid,
                                                     qid=qid)
        assert len(mmap) > old_mmap_len, (old_mmap_len, len(mmap))
        mmap[0] = old_mmap_statuscode
        assert mmap[0] != INVALID

        return mmap

    def __reconnect_to_mmap(self,
                            pid: int,
                            qid: int,
                            mmap):

        #debug(f"Server: memory map has been marked as invalid")
        prev_len = len(mmap)
        mmap.close()
        mmap = self.resource_manager.connect_to_pid_mmap(pid, qid)

        # Make sure it actually is larger than the previous one,
        # so as to reduce the risk of an infinite loop
        assert len(mmap) > prev_len, \
            f"[pid {pid}:qid {qid}] " \
            f"New memory map should be larger than the previous one: " \
            f"{len(mmap)} !> {prev_len}"
        return mmap
