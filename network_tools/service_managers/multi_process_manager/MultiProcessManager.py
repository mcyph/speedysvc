import os
import time
import socket
import signal
import psutil
import _thread
from multiprocessing import cpu_count

from network_tools.logger.LoggerClient import LoggerClient
from network_tools.rpc.network.NetworkServer import NetworkServer


class MultiProcessServer:
    def __init__(self,
                 service_time_series_data,
                 logger_server,
                 server_methods,
                 *server_providers,

                 tcp_bind_address=None,

                 min_proc_num=1,
                 max_proc_num=cpu_count(),
                 max_proc_mem_bytes=None,

                 new_proc_cpu_pc=0.3,
                 new_proc_avg_over_secs=20,
                 kill_proc_avg_over_secs=240
                 ):
        """

        """

        self.service_time_series_data = service_time_series_data
        self.logger_server = logger_server
        self.server_methods = server_methods # This should probably always be callable directly, so as to be able to create them in the child processes
        self.server_providers = server_providers

        self.tcp_bind_address = tcp_bind_address

        self.min_proc_num = min_proc_num
        self.max_proc_num = max_proc_num
        self.max_proc_mem_bytes = max_proc_mem_bytes

        self.new_proc_cpu_pc = new_proc_cpu_pc
        self.new_proc_avg_over_secs = new_proc_avg_over_secs
        self.kill_proc_avg_over_secs = kill_proc_avg_over_secs

        assert 0.0 < new_proc_cpu_pc < 1.0, \
            "The overall percentage CPU usage before starting a new " \
            "process should be between 0.0 and 1.0 non-inclusive"

        # Make sure tcp_bind_address has been provided as needed
        # The reason for binding here in the parent process,
        # is to make it so that the child processes can listen
        # on the same socket, eliminating the need to use other
        # forms of IPC.
        tcp_needed = False

        for provider in server_providers:
            if isinstance(provider, NetworkServer):
                tcp_needed = True

        if not tcp_needed and tcp_bind_address:
            raise Exception(
                f"TCP specified as being bound to address "
                f"{tcp_bind_address}, but no TCP server class "
                f"provided to implementations!"
            )
        elif tcp_needed and not tcp_bind_address:
            raise Exception(
                f"TCP not specified as being bound to an address "
                f"while a TCP server class was provided to "
                f"implementations!"
            )

        if tcp_bind_address:
            sock = self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
                # TODO: FIX LATENCY PARAMS!!!! ========================================================================
            )
            sock.bind((tcp_bind_address, server_methods.port))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.listen(0)

        # Collect data periodically
        self.LPIDs = []
        self.last_proc_op_time = 0
        _thread.start_new_thread(self.__monitor_process_loop, ())

    def __monitor_process_loop(self):
        """
        # TODO:
        # * Spawn new worker processes which exceed
        #   process time over a given time period
        # * Kill worker processes when they aren't needed?
        #   TODO: How to make sure all requests are processed before the process shuts down??
        #         Possibly add a signal handler for SIGKILL that tells the handler
        #         "shut down after this next call is finished, (potentially) without
        #         freeing some resources"?
        # * Respawn in case of crashes
        """

        while True:
            for pid in self.LPIDs[:]:
                if not psutil.pid_exists(pid):
                    self.remove_proc(pid) # NOT IDIOMATIC!!!!!

            if len(self.LPIDs) < self.min_proc_num:
                # Maybe best to start a new thread, so this loop
                # doesn't run in the child process? ==========================================================
                _thread.start_new_thread(self.new_proc, ())

            DAverages = self.service_time_series_data.FIXME()
            time_since_last_op = time.time()-self.last_proc_op_time

            if (
                self.max_proc_mem_bytes is not None and
                DAverages[FIXME] > self.max_proc_mem_bytes
            ):
                # Reap processes until we don't exceed
                # the maximum amount of memory
                self.remove_proc()
            elif (
                time_since_last_op < self.new_proc_avg_over_secs and
                DAverages[FIXME] > self.new_proc_cpu_pc and
                len(self.LPIDs) <= self.max_proc_num
            ):
                # Start a new worker process if the CPU usage is higher
                # than a certain amount over the provided period
                # new_proc_avg_over_secs
                self.new_proc()
            elif (
                time_since_last_op < self.kill_proc_avg_over_secs and
                DAverages[FIXME] < self.new_proc_cpu_pc
            ):
                # Reduce the number of workers if they aren't being
                # used over an extended period
                self.remove_proc()

    #========================================================#
    #                  Start/Stop Processes                  #
    #========================================================#

    def new_proc(self):
        """

        """
        pid = os.fork()

        if pid == 0:
            # In child process
            logger_client = LoggerClient() # TODO: FINISH IMPLEMENTING ME!!! ========================================

            L = []
            for provider in self.server_providers:
                if isinstance(provider, NetworkServer):
                    L.append(provider(server=self.sock))
                else:
                    L.append(provider()) # Should this be __call__()??? =================================================

            while 1:
                time.sleep(10)
        else:
            # In parent - pid of child returned
            self.LPIDs.append(pid)
            self.service_time_series_data.add_pid(pid)

    def remove_proc(self, pid=None):
        """

        """
        if pid is None:
            pid = self.LPIDs[-1]

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
