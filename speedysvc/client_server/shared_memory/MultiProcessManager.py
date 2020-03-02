import sys, os
import time
import json
import signal
import random
import psutil
import _thread
import importlib
import subprocess
from sys import argv
from os import getpid
from multiprocessing import cpu_count
from speedysvc.kill_pid_and_children import kill_pid_and_children

from speedysvc.logger.std_logging.LoggerClient import LoggerClient
from speedysvc.client_server.network.NetworkServer import NetworkServer
from speedysvc.client_server.shared_memory.SHMResourceManager import \
    SHMResourceManager, CONNECT_TO_EXISTING
from hybrid_lock import SemaphoreDestroyedException


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
                 import_from, section, server_methods,
                 tcp_bind=None,
                 tcp_allow_insecure_serialisation=False,

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

        :param import_from: the module the import the server class from
        :param section: the server class name
        :param server_methods: the server methods class. Should be a class
                               which has yet to be instantiated, so that
                               it can be created by child worker processes.

        :param tcp_bind:
        :param tcp_allow_insecure_serialisation:

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
        self.import_from = import_from
        self.section = section

        # This should probably always be callable directly,
        # so as to be able to create them in the child processes
        self.server_methods = server_methods

        self.tcp_bind = tcp_bind
        self.tcp_allow_insecure_serialisation = tcp_allow_insecure_serialisation

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

        # Get the SHMResourceManager to clean up
        # any previously created server processes
        # TODO: Also add capability to clean up previous MultiProcessManager's!
        # TODO: It would also be nice to remove self.LPIDs, and only rely on
        #   SHMResourceManager for storing server worker PIDs
        # OPEN ISSUE: Should check_for_missing_pids be called periodically?
        self.resource_manager = SHMResourceManager(self.port, self.name)
        self.resource_manager.check_for_missing_pids()
        self.resource_manager.reset_all_server_pids(kill=True)

        # Collect data periodically
        self.LPIDs = []
        self.last_proc_op_time = 0
        self.shutting_down = False
        self.started_collecting_data = False
        self.logger_client = LoggerClient(server_methods)

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

        while (
            (not self.shutting_down) and
            (self.logger_client.get_service_status() not in (
                'stopping', 'stopped'
            ))
        ):
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

            DNewProcAvg = self.logger_client.get_average_over(
                time.time() - self.new_proc_avg_over_secs, time.time()
            )
            DRemoveProcAvg = self.logger_client.get_average_over(
                time.time() - self.kill_proc_avg_over_secs, time.time()
            )
            DLastRecord = self.logger_client.get_last_record()
            time_since_last_op = time.time()-self.last_proc_op_time
            #print(f"{self.server_methods.name} DNEWPROCAVG:", DNewProcAvg)

            if not DNewProcAvg or not DRemoveProcAvg:
                time.sleep(MONITOR_PROCESS_EVERY_SECS)
                continue

            if (
                self.max_proc_mem_bytes is not None and
                DLastRecord['physical_mem'] > self.max_proc_mem_bytes  # What about virtual memory?? ==============
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
        assert self.logger_client.get_service_status() == 'stopped', \
            "Can't start a service that isn't stopped!"
        self.logger_client.set_service_status('starting')

        for x in range(self.min_proc_num):
            # Make sure the initial processes have booted up
            # from the main thread, so it can block as necessary
            # (assuming wait_until_completed is set)
            self.new_child_process()

        if self.tcp_bind:
            def start_network_server():
                while not self.logger_client.get_service_status() == 'started':
                    # Wait till the SHMServer can be connected to
                    time.sleep(0.1)

                self.network_server = NetworkServer(
                    tcp_bind_address=self.tcp_bind,
                    server_methods=self.server_methods,
                    force_insecure_serialisation=self.tcp_allow_insecure_serialisation
                )(self.server_methods)

            _thread.start_new_thread(start_network_server, ())
        _thread.start_new_thread(self.__monitor_process_loop, ())

    def stop_service(self):
        """
        Stop a started service.
        """
        assert self.logger_client.get_service_status() == 'started', \
            "Can't stop a service that isn't started!"
        self.shutting_down = True
        self.logger_client.set_service_status('stopping')

        while self.LPIDs:
            self.remove_child_process()
        self.logger_client.set_service_status('stopped')
        self.logger_client.shutdown()

    def new_child_process(self):
        """
        Create a new worker process
        """
        DEnv = os.environ.copy()
        DEnv["PATH"] = "/usr/sbin:/sbin:" + DEnv["PATH"]
        DArgs = {
            'import_from': self.import_from,
            'section': self.section,
        }
        if False:
            from speedysvc.client_server.shared_memory._service_worker import _service_worker
            from os import fork

            pid = fork()

            # Note that the server_methods needs to be after to fork()
            # in order to make sure any module-level SHMClients report
            # correct values with getpid(), and so we won't waste
            # memory in this management process!
            DArgs['server_methods'] = getattr(
                importlib.import_module(DArgs.pop('import_from')),
                DArgs.pop('section')
            )
            if pid == 0:
                # in child
                _service_worker(**DArgs)
        else:
            proc = subprocess.Popen([
                'python3', '-m',
                'speedysvc.client_server.shared_memory._service_worker',
                json.dumps(DArgs)
            ], env=DEnv)
            pid = proc.pid

        self.logger_client.add_pid(pid)
        self.last_proc_op_time = time.time()
        self.LPIDs.append(pid)

        def start_collecting_data():
            while not self.logger_client.get_service_status() == 'started':
                time.sleep(0.1)

            if not self.started_collecting_data:
                # The service time series data should only start
                # once the process has started up
                self.started_collecting_data = True
                self.logger_client.start_collecting()

        if self.wait_until_completed:
            print(f"{self.server_methods.name} parent: "
                  f"Waiting for child to initialise...")
            while not self.logger_client.get_service_status() == 'started':
                time.sleep(0.1)
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

        # Lock the service, to make sure we don't
        # terminate it halfway through a call!
        LLocks = self.__get_L_client_locks()
        self.__lock_client_locks(LLocks)

        try:
            if pid is None:
                pid = random.choice(self.LPIDs)

            self.last_proc_op_time = time.time()
            self.LPIDs.remove(pid)
            try:
                self.logger_client.remove_pid(pid)
            except:
                pass

            if psutil.pid_exists(pid):
                kill_pid_and_children(pid)
        finally:
            self.__unlock_client_locks(LLocks)

    #========================================================#
    #              Acquire/Release Server Locks              #
    #========================================================#

    def __get_L_client_locks(self):
        """

        :return:
        """
        L = []
        for pid, qid in self.resource_manager.get_client_pids():
            client_lock = self.resource_manager.get_client_lock(
                pid, qid, CONNECT_TO_EXISTING
            )
            L.append(client_lock)
        return L

    def __lock_client_locks(self, LLocks):
        """

        :param LLocks:
        :return:
        """
        for lock in LLocks:
            try:
                lock.lock()
            except SemaphoreDestroyedException:
                pass
            except:
                import traceback
                traceback.print_exc()

    def __unlock_client_locks(self, LLocks):
        """

        :param LLocks:
        :return:
        """
        for lock in LLocks:
            try:
                lock.unlock()
            except SemaphoreDestroyedException:
                pass
            except:
                import traceback
                traceback.print_exc()

    def __unlock_client_locks_for_dead_pids(self, LLocks):
        """
        TODO: If a server lock's reported PID no longer exists
          (possibly due to it crashing due to a segfault etc),
          release it!!

        :param LLocks:
        :return:
        """
        FIXME


if __name__ == '__main__':
    DArgs = json.loads(argv[-1])
    DArgs['server_methods'] = getattr(
        importlib.import_module(DArgs['import_from']),
        DArgs['section']
    )
    mps = MultiProcessServer(**DArgs)

    _handling_sigint = [False]
    def signal_handler(sig, frame):
        if _handling_sigint[0]: return
        _handling_sigint[0] = True
        print(f"MultiProcessManager [{getpid()}]: "
              f"exiting PIDs {mps.LPIDs}")
        mps.stop_service()
        print("MultiProcesssManager: "
              "exiting", getpid())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    while 1:
        signal.pause()