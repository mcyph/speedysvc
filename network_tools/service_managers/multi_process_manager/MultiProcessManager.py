import os
import time
import socket
import signal
import psutil
import _thread
from multiprocessing import cpu_count

from network_tools.logger.LoggerClient import LoggerClient
from network_tools.rpc.network.NetworkServer import NetworkServer
from network_tools.rpc.shared_memory.SHMServer import SHMServer


MONITOR_PROCESS_EVERY_SECS = 5


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

        """

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

        if wait_until_completed:
            for x in range(min_proc_num):
                # Make sure the initial processes have booted up
                # from the main thread, so it can block as necessary
                # (assuming wait_until_completed is set)
                self.new_proc()

        _thread.start_new_thread(self.__monitor_process_loop, ())

    def __monitor_process_loop(self):
        """
        * Spawn new worker processes which exceed
          process time over a given time period
        * Kill worker processes when they aren't needed?
          TODO: How to make sure all requests are processed before
                the process shuts down??
                Possibly add a signal handler for SIGKILL that tells
                the handler "shut down after this next call is
                finished, (potentially) without freeing some
                resources"? -> DONE, NEEDS TO BE TESTED!
        * Respawn in case of crashes
        """
        print(f"{self.server_methods.name}: Process monitor started")

        while True:
            for pid in self.LPIDs[:]:
                if not psutil.pid_exists(pid):
                    self.remove_proc(pid)

            if (
                len(self.LPIDs) < self.min_proc_num
            ):
                # Start a new worker process if there aren't enough
                print(f"{self.server_methods.name}: "
                      f"Adding worker process due to "
                      f"minimum processes not satisfied")
                self.new_proc()
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
                self.remove_proc()

            elif (
                time_since_last_op > self.new_proc_avg_over_secs and
                (DNewProcAvg['cpu_usage_pc'] / DNewProcAvg['num_processes']) >
                    self.new_proc_cpu_pc and
                len(self.LPIDs) < self.max_proc_num
            ):
                # Start a new worker process if the CPU usage is higher
                # than a certain amount over the provided period
                # new_proc_avg_over_secs
                print(f"{self.server_methods.name}: "
                      f"Adding worker process due to CPU higher than "
                      f"{int(self.new_proc_cpu_pc*100)}% over "
                      f"{self.new_proc_avg_over_secs} seconds")
                self.new_proc()

            elif (
                time_since_last_op > self.kill_proc_avg_over_secs and
                DRemoveProcAvg['cpu_usage_pc'] < self.new_proc_cpu_pc and
                len(self.LPIDs) > self.min_proc_num
            ):
                # Reduce the number of workers if they aren't being
                # used over an extended period
                print(f"{self.server_methods.name}: "
                      f"Removing process due to CPU lower than "
                      f"{int(self.new_proc_cpu_pc * 100)}% over "
                      f"{self.kill_proc_avg_over_secs} seconds")
                self.remove_proc()

            time.sleep(MONITOR_PROCESS_EVERY_SECS)

    #========================================================#
    #                  Start/Stop Processes                  #
    #========================================================#

    def new_proc(self):
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

            while 1:
                time.sleep(10)
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

    def remove_proc(self, pid=None):
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
            # Try to end process cleanly
            # SIGINT -> SIGTERM -> SIGKILL
            os.kill(pid, signal.SIGINT)

            # =1secs to finish current call
            for x in range(10):
                if not psutil.pid_exists(pid):
                    break
                time.sleep(0.1)
            os.kill(pid, signal.SIGTERM)

            # =5secs to finish ending process
            for x in range(50):
                if not psutil.pid_exists(pid):
                    break
                time.sleep(0.1)

            if psutil.pid_exists(pid):
                # Kill it good if it doesn't respond
                os.kill(pid, signal.SIGKILL)

            # Clean up potential zombie in OS process table
            try:
                os.waitpid(pid, 0)
            except:
                import traceback
                traceback.print_exc()

