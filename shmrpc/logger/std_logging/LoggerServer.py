import time
import psutil
from _thread import allocate_lock, start_new_thread

from shmrpc.rpc.shared_memory.SHMServer import SHMServer
from shmrpc.rpc_decorators import raw_method, json_method
from shmrpc.logger.std_logging.log_entry_types import \
    dict_to_log_entry, STDERR, STDOUT
from shmrpc.logger.std_logging.FIFOJSONLog import FIFOJSONLog
from shmrpc.logger.time_series_data.ServiceTimeSeriesData import ServiceTimeSeriesData


FLUSH_EVERY_SECONDS = 1.0


class LoggerServer:
    def __init__(self, log_dir, server_methods,
                 fifo_json_log_parent=None):
        """

        :param log_dir:
        :param server_methods:
        """
        self.original_server_methods = server_methods
        self.status = 'stopped'
        self.LPIDs = []

        # NOTE ME: I'm overriding the port so as to not have a
        #          collision with the existing (integer) port,
        #          used by the original server.
        self.port = f'{server_methods.port}_log'
        self.name = f'{server_methods.name}_log'
        self.shm_server = SHMServer()

        # Store the single value stats
        # (e.g. how long each individual call takes,
        # and how many times each call has taken place)
        # which would take too long to store separately
        self.DMethodStats = {}

        # Open the stdout/stderr files
        self.stdout_lock = allocate_lock()
        self.f_stdout = open(
            f'{log_dir}/{self.name}.stdout', 'ab+',
            buffering=8192
        ) # binary??
        self.stderr_lock = allocate_lock()
        self.f_stderr = open(
            f'{log_dir}/{self.name}.stderr', 'ab+',
            buffering=8192 # LINE BUFFERED!
        )

        # Create the memory cached log
        self.fifo_json_log = FIFOJSONLog(
            path=f'{log_dir}/{self.name}.log.json',
            parent_logger=fifo_json_log_parent
        )
        # Create the time series statistics data instance
        # (e.g. to record how much RAM etc each process is using)
        self.service_time_series_data = ServiceTimeSeriesData(
            path=f'{log_dir}/time_series_data.bin'
        )

        # Start the server
        self.shm_server(
            server_methods=self,
            init_resources=True,
            use_spinlock=False # NOTE ME: This is normally called in the background, and performance shouldn't be a priority here
        )

        self.flush_needed = False
        start_new_thread(self.__flush_loop, ())

    def __flush_loop(self):
        """
        Only flush the files periodically, so as to
        reduce the amount IO affects performance
        """
        if self.flush_needed:
            with self.stderr_lock:
                self.f_stderr.flush()
            with self.stdout_lock:
                self.f_stdout.flush()
            with self.stdout_lock:
                with self.stderr_lock:
                    self.fifo_json_log.flush()
            self.flush_needed = False
        time.sleep(FLUSH_EVERY_SECONDS)

    #=========================================================#
    #                Update Method Statistics                 #
    #=========================================================#

    @json_method
    def _update_method_stats_(self, pid, DMethodStats):
        """
        Send method statistics to the central management interface
        (i.e. this process) to allow for benchmarks periodically

        :param pid: the process ID of the calling worker
        :param DMethodStats: the method statistics
        """

        # OPEN ISSUE: While this class is called "LoggerServer", I can't
        # currently think of a better place to put this, as this is
        # effectively a communications system from worker
        # servers->worker manager - perhaps this class should be
        # renamed to reflect its broader scope?
        #SHMServerprint("LOGGER SERVER UPDATE STATS:", pid)

        self.DMethodStats[pid] = DMethodStats

    def get_D_method_stats(self):
        """


        :return:
        """
        #print("LOGGER SERVER GET METHOD STATS:")
        D = {}

        for pid, DMethodStats in self.DMethodStats.items():
            for method_name, DMethodStat in DMethodStats.items():
                D.setdefault(method_name, {
                    'num_calls': 0,
                    'total_time': 0
                })
                D[method_name]['num_calls'] += DMethodStat['num_calls']
                D[method_name]['total_time'] += DMethodStat['total_time']

        for method_name, i_D in D.items():
            if i_D['num_calls'] != 0:
                i_D['avg_call_time'] = i_D['total_time'] / i_D['num_calls']
            else:
                i_D['avg_call_time'] = 0  # NOTE ME: Haven't got stats yet?

        return D

    #=========================================================#
    #                 Write to stdout/stderr                  #
    #=========================================================#

    @json_method
    def _write_to_log_(self, t, pid, port, service_name, msg, level):
        """

        :param t: the time when the log entry occurred
        :param pid: the process ID from which the event occurred
        :param port: the port of the service
        :param service_name: the name of the service
        :param msg: the log message
        :param level: a log level, e.g. ERROR, or INFO
        """
        log_entry = dict_to_log_entry({
            't': t,
            'pid': pid,
            'port': port,
            'svc': service_name,
            'msg': msg,
            'level': level
        })

        if log_entry.writes_to == STDERR:
            with self.stderr_lock:
                self.f_stderr.write(log_entry.to_text().encode('utf-8'))
                self.flush_needed = True
        elif log_entry.writes_to == STDOUT:
            with self.stdout_lock:
                self.f_stdout.write(log_entry.to_text().encode('utf-8'))
                self.flush_needed = True
        else:
            # Should never get here!
            raise Exception("Unknown writes_to: %s" % log_entry.writes_to)

        try:
            self.fifo_json_log.write_to_log(
                **log_entry.to_dict()
            )
        except OverflowError:
            import warnings
            warnings.warn("Warning: message overflow in fifo_json_log")

    #=========================================================#
    #                     Service Status                      #
    #=========================================================#

    @json_method
    def get_service_status(self):
        """

        :return:
        """
        #print("LOGGER SERVER GET STATUS:")
        return self.status

    @json_method
    def set_service_status(self, status):
        """

        :param status:
        :return:
        """
        #print("LOGGER SERVER STATUS:", status)
        if status == 'started':
            self.loaded_ok = True
        elif status == 'stopped':
            self.loaded_ok = False

            # Clean out previous PIDs
            for pid in self.LPIDs:
                if psutil.pid_exists(pid):
                    import warnings
                    warnings.warn(f"PID {pid} for service {self.name}:{self.port} "
                                  f"still exists when it should have been killed!")
            self.LPIDs = []

        self.status = status

    #=========================================================#
    #                Service Time Series Data                 #
    #=========================================================#

    @json_method
    def get_average_over(self, from_time, to_time):
        """

        :param from_time:
        :param to_time:
        :return:
        """
        return self.service_time_series_data.get_average_over(
            from_time, to_time
        )

    @json_method
    def add_pid(self, pid):
        """

        :param pid:
        :return:
        """
        #print("LOGGER SERVER ADD PID", pid)
        self.LPIDs.append(pid)
        self.service_time_series_data.add_pid(pid)

    @json_method
    def remove_pid(self, pid):
        """

        :param pid:
        :return:
        """
        #print("LOGGER SERVER REMOVE PID", pid)
        self.LPIDs.pop(pid)
        self.service_time_series_data.remove_pid(pid)
        del self.DMethodStats[pid]

    @json_method
    def start_collecting(self):
        """

        :return:
        """
        #print("LOGGER SERVER START COLLECTING:")
        self.service_time_series_data.start_collecting()

    @json_method
    def stop_collecting(self):
        """

        :return:
        """
        self.service_time_series_data.stop_collecting()
