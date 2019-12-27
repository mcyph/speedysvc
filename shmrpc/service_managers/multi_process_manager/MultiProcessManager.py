import os
import time
import socket
import signal
import psutil
import _thread
from multiprocessing import cpu_count

from shmrpc.logger.LoggerClient import LoggerClient
from shmrpc.rpc.network.NetworkServer import NetworkServer
from shmrpc.rpc.shared_memory.SHMServer import SHMServer


MONITOR_PROCESS_EVERY_SECS = 5

STARTED = 0
STOPPED = 1
STOPPING = 2
STARTING = 3

_DStatusStrings = {
    STARTED: 'started',
    STOPPED: 'stopped',
    STOPPING: 'stopping',
    STARTING: 'starting',
}


class MultiProcessServer:
    def __init__(self,
                 service_time_series_data,
                 logger_server,
                 server_methods,
                 *server_providers,

                 min_proc_num=1,
                 max_proc_num=cpu_count(),
                 max_proc_mem_bytes=None,

                 new_proc_cpu_pc=0.3,
                 new_proc_avg_over_secs=20,
                 kill_proc_avg_over_secs=240,

                 wait_until_completed=True
                 ):
        """
        Create a manager for a given service, which has child worker processes.

        This monitors children, restarting them if they crash.
        It also creates new children if the combined CPU usage is above
        a certain threshold for a given time period. It also removes
        children if they are below a combined CPU usage amount over
        a given period.
        Optionally also removed child processes if combined RAM usage
        exceeds a certain amount.

        :param service_time_series_data: a ServiceTimeSeriesData instance,
                                         for logging process information
                                         like CPU usage
        :param logger_server: a LoggerServer instance
        :param server_methods: the server methods class. Should be a class
                               which has yet to be instantiated, so that
                               it can be created by child worker processes.
        :param server_providers: Server implementation instances. Currently
                                 one of SHMServer or NetworkServer.
        :param min_proc_num: the minimum number of worker processes.
                             If the number of children falls below this
                             number, they will be recreated.
        :param max_proc_num: the maximum number of worker processes
        :param max_proc_mem_bytes: The maximum amount of memory all
                                   worker processes as a whole are
                                   allowed to occupy in bytes.
        :param new_proc_cpu_pc: The combined CPU percentage between 0.0 and
                                1.0, above which to start a new child worker.
        :param new_proc_avg_over_secs: The time period over which to average
                                       the combined CPU percentage when
                                       creating new children.
        :param kill_proc_avg_over_secs: The time period over which to average
                                        the combined CPU percentage when
                                        removing existing children.
        :param wait_until_completed: Whether to block until at least one
                                     child worker has been created.
                                     Useful if other services will depend on
                                     this one, but can increase service load
                                     times.
        """
        self.port = server_methods.port
        self.name = server_methods.name

        self.service_time_series_data = service_time_series_data
        self.logger_server = logger_server
        # This should probably always be callable directly,
        # so as to be able to create them in the child processes
        self.server_methods = server_methods
        self.server_providers = server_providers

        self.min_proc_num = min_proc_num
        self.max_proc_num = max_proc_num
        self.max_proc_mem_bytes = max_proc_mem_bytes

        self.new_proc_cpu_pc = new_proc_cpu_pc
        self.new_proc_avg_over_secs = new_proc_avg_over_secs
        self.kill_proc_avg_over_secs = kill_proc_avg_over_secs

        self.wait_until_completed = wait_until_completed

        assert 0.0 < new_proc_cpu_pc < 1.0, \
            "The overall percentage CPU usage before starting a new " \
            "process should be between 0.0 and 1.0 non-inclusive"

        # Collect data periodically
        self.LPIDs = []
        self.last_proc_op_time = 0
        self.started_collecting_data = False
        self.status = STOPPED

        self.start_service()

    def __monitor_process_loop(self):
        """
        * Spawn new worker processes which exceed
          process time over a given time period
        * Kill worker processes when they aren't needed?
          (Note: In order to make sure all requests are processed before
                 the process shuts down, a signal handler for SIGINT
                 that tells the handler "shut down after this next call is
                 finished, (potentially) without freeing some
                 resources" is set in child SHMServers)
        * Respawn in case of crashes
        """
        print(f"{self.server_methods.name}: Process monitor started")

        while self.status == STARTED:
            for pid in self.LPIDs[:]:
                try:
                    if not psutil.pid_exists(pid):
                        # Stop monitoring child processes that no longer exist.
                        self.remove_child_process(pid)
                    else:
                        proc = psutil.Process(pid)
                        if proc.status() == psutil.STATUS_ZOMBIE:
                            # Process no longer exists except on process table.
                            os.waitpid(pid, 0)
                            self.remove_child_process(pid)
                except:
                    import traceback
                    traceback.print_exc()

            if (
                len(self.LPIDs) < self.min_proc_num
            ):
                # Start a new worker process if there aren't enough
                print(f"{self.server_methods.name}: "
                      f"Adding worker process due to "
                      f"minimum processes not satisfied")
                self.new_child_process()
                time.sleep(MONITOR_PROCESS_EVERY_SECS)
                continue

            DNewProcAvg = self.service_time_series_data.get_average_over(
                time.time() - self.new_proc_avg_over_secs, time.time()
            )
            DRemoveProcAvg = self.service_time_series_data.get_average_over(
                time.time() - self.kill_proc_avg_over_secs, time.time()
            )
            time_since_last_op = time.time()-self.last_proc_op_time
            #print(f"{self.server_methods.name} DNEWPROCAVG:", DNewProcAvg)

            if not DNewProcAvg or not DRemoveProcAvg:
                time.sleep(MONITOR_PROCESS_EVERY_SECS)
                continue

            if (
                self.max_proc_mem_bytes is not None and
                DRemoveProcAvg['physical_mem'] > self.max_proc_mem_bytes # What about virtual memory?? ==============
            ):
                # Reap processes until we don't exceed
                # the maximum amount of memory
                print(f"{self.server_methods.name}: "
                      f"Removing process due to memory exceeded")
                self.remove_child_process()

            elif (
                time_since_last_op > self.new_proc_avg_over_secs and
                (DNewProcAvg['cpu_usage_pc'] / DNewProcAvg['num_processes']) >
                    (self.new_proc_cpu_pc * 100.0) and
                len(self.LPIDs) < self.max_proc_num
            ):
                # Start a new worker process if the CPU usage is higher
                # than a certain amount over the provided period
                # new_proc_avg_over_secs
                print(f"{self.server_methods.name}: "
                      f"Adding worker process due to CPU higher than "
                      f"{int(self.new_proc_cpu_pc*100)}% over "
                      f"{self.new_proc_avg_over_secs} seconds")
                self.new_child_process()

            elif (
                time_since_last_op > self.kill_proc_avg_over_secs and
                DRemoveProcAvg['cpu_usage_pc'] < (self.new_proc_cpu_pc * 100.0) and
                len(self.LPIDs) > self.min_proc_num
            ):
                # Reduce the number of workers if they aren't being
                # used over an extended period
                print(f"{self.server_methods.name}: "
                      f"Removing process due to CPU lower than "
                      f"{int(self.new_proc_cpu_pc*100)}% over "
                      f"{self.kill_proc_avg_over_secs} seconds")
                self.remove_child_process()

            time.sleep(MONITOR_PROCESS_EVERY_SECS)

    #========================================================#
    #                  Start/Stop Processes                  #
    #========================================================#

    def get_status(self):
        return self.status

    def get_status_as_string(self):
        return _DStatusStrings[self.status]

    def restart_service(self):
        """
        Stop then start a running service.
        """
        self.stop_service()
        self.start_service()

    def start_service(self):
        """
        Start a stopped service.
        """
        assert self.status == STOPPED, \
            "Can't start a service that isn't stopped!"
        self.status = STARTING

        if self.wait_until_completed:
            for x in range(self.min_proc_num):
                # Make sure the initial processes have booted up
                # from the main thread, so it can block as necessary
                # (assuming wait_until_completed is set)
                self.new_child_process()

        self.status = STARTED
        _thread.start_new_thread(self.__monitor_process_loop, ())

    def stop_service(self):
        """
        Stop a started service.
        """
        assert self.status == STARTED, \
            "Can't stop a service that isn't started!"
        self.status = STOPPING

        while self.LPIDs:
            self.remove_child_process()

        self.status = STOPPED

    def new_child_process(self):
        """
        Create a new worker process
        """
        pid = os.fork()

        if pid == 0:
            # In child process
            print(f"{self.server_methods.name} child: "
                  f"Creating logger client")
            self.logger_client = LoggerClient(self.server_methods)
            print(f"{self.server_methods.name} child: "
                  f"Creating server methods")
            smi = self.server_methods()
            print(f"{self.server_methods.name} child: "
                  f"Server methods created, starting implementations")

            L = []
            for provider in self.server_providers:
                if isinstance(provider, NetworkServer):
                    L.append(provider(
                        server_methods=smi
                    ))
                elif isinstance(provider, SHMServer):
                    L.append(provider(
                        server_methods=smi,
                        init_resources=len(self.LPIDs) == 0
                    ))
                else:
                    L.append(provider(
                        server_methods=smi
                    ))

            # Tell the logger server that a child has properly loaded:
            # this helps to make sure if processes are loaded properly,
            # if one depends on another.
            self.logger_client.loaded_ok_signal()

            try:
                while 1:
                    time.sleep(10)
            except KeyboardInterrupt:
                from os import getpid

                print(f"Intercepted keyboard interrupt for {self.name} [PID {getpid()}]")
                for inst in L:
                    if hasattr(inst, 'shutdown'):
                        print(f"Calling shutdown for {self.name} [PID {getpid()}]..")
                        inst.shutdown()
                        print(f"Shutdown OK for {self.name} [PID {getpid()}]")

                time.sleep(2)

        else:
            # In parent - pid of child returned
            self.last_proc_op_time = time.time()
            self.LPIDs.append(pid)
            self.service_time_series_data.add_pid(pid)

            def start_collecting_data():
                while not self.logger_server.loaded_ok:
                    time.sleep(0.05)

                if not self.started_collecting_data:
                    # The service time series data should only start
                    # once the process has started up
                    self.started_collecting_data = True
                    self.service_time_series_data.start_collecting()

            if self.wait_until_completed:
                print(f"{self.server_methods.name} parent: "
                      f"Waiting for child to initialise...")
                while not self.logger_server.loaded_ok:
                    time.sleep(0.05)
                print(f"{self.server_methods.name} parent: "
                      f"child signaled it has initialised OK")

                start_collecting_data()
            else:
                _thread.start_new_thread(start_collecting_data, ())

    def remove_child_process(self, pid=None):
        """
        Remove process with `pid` if specified;
        otherwise remove the most recently-created process
        """
        if pid is None:
            pid = self.LPIDs[-1]

        self.last_proc_op_time = time.time()
        self.LPIDs.remove(pid)
        self.service_time_series_data.remove_pid(pid)

        if psutil.pid_exists(pid):
            MAX_SECS_TO_WAIT_AFTER_SIGINT = 100

            # Try to end process cleanly
            # SIGINT -> SIGTERM -> SIGKILL
            os.kill(pid, signal.SIGINT)

            # =Xsecs to finish current call
            for x in range(MAX_SECS_TO_WAIT_AFTER_SIGINT * 10):
                if not psutil.pid_exists(pid):
                    break
                try:
                    proc = psutil.Process(pid)
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        break
                except:
                    print(f"Can't get pid [{pid}] status - assuming it's exited?")
                    break
                time.sleep(0.1)

            if psutil.pid_exists(pid):
                print(f"Killing PID with SIGTERM [{pid}]")
                os.kill(pid, signal.SIGTERM)

            # =5secs to finish ending process
            #for x in range(50):
            #    if not psutil.pid_exists(pid):
            #        break
            #    time.sleep(0.1)

            #if psutil.pid_exists(pid):
            #    # Kill it good if it doesn't respond
            #    os.kill(pid, signal.SIGKILL)

            # Clean up potential zombie in OS process table
            try:
                print(f"Waiting for PID {pid} to exit")
                os.waitpid(pid, 0)
                print(f"Process {pid} exited OK")
            except:
                import traceback
                traceback.print_exc()
