import time
import psutil
from _thread import allocate_lock, start_new_thread

from speedysvc.client_server.shared_memory.SHMServer import SHMServer
from speedysvc.service_method import service_method
from speedysvc.logger.std_logging.log_entry_types import \
    dict_to_log_entry, STDERR, STDOUT
from speedysvc.logger.std_logging.FIFOJSONLog import FIFOJSONLog
from speedysvc.logger.time_series_data.ServiceTimeSeriesData import ServiceTimeSeriesData

FLUSH_EVERY_SECONDS = 3.0

_flush_loop_started = [False]
_LLoggerServers = []


def _check_flush_needed_loop():
    """
    Monitor whether a flush to disk of the logs is
    needed in a single thread to minimize resources
    """
    while True:
        if not _LLoggerServers:
            _flush_loop_started[0] = False
            return

        for logger_server in _LLoggerServers[:]:
            try:
                if logger_server.shm_server.shut_me_down:
                    _LLoggerServers.remove(logger_server)
                else:
                    logger_server.flush()
            except:
                import traceback
                traceback.print_exc()

        time.sleep(FLUSH_EVERY_SECONDS)


class LoggerServer:
    def __init__(self,
                 log_dir: str,
                 server_name: str,
                 server_port: int,
                 fifo_json_log_parent=None):

        self.status = 'stopped'
        self.LPIDs = []

        # NOTE ME: I'm overriding the port to not have a
        #          collision with the existing (integer) port,
        #          used by the original server.
        self.port = port = f'{server_port}_log'
        self.name = f'{server_name}_log'

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
        )  # binary??
        self.stderr_lock = allocate_lock()
        self.f_stderr = open(
            f'{log_dir}/{self.name}.stderr', 'ab+',
            buffering=8192  # LINE BUFFERED!
        )

        # Create the memory cached log
        self.fifo_json_log = FIFOJSONLog(
            path=f'{log_dir}/{self.name}.log.json',
            parent_logger=fifo_json_log_parent
        )
        # Create the time series statistics data instance
        # (e.g. to record how much RAM etc each process is using)
        self.service_time_series_data = ServiceTimeSeriesData(start_collecting_immediately=False)

        # Start the server
        assert port == self.port, (port, self.port)
        self.shm_server = SHMServer(
            server_methods=self,
            use_spinlock=False,
            port=self.port,
            service_name=self.name,
            # NOTE ME: This is normally called in the background, and performance shouldn't be a priority here
        )
        self.shm_server.serve_forever_in_new_thread()

        self.flush_needed = False
        _LLoggerServers.append(self)
        if not _flush_loop_started[0]:
            _flush_loop_started[0] = True
            start_new_thread(_check_flush_needed_loop, ())

    def flush(self):
        """
        Only flush the files periodically to reduce
        the amount IO affects performance
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

    # =========================================================#
    #                Update Method Statistics                 #
    # =========================================================#

    @service_method()
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
        # SHMServerprint("LOGGER SERVER UPDATE STATS:", pid)

        self.DMethodStats[pid] = DMethodStats

    def get_D_method_stats(self):
        # print("LOGGER SERVER GET METHOD STATS:")
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

    # =========================================================#
    #                 Write to stdout/stderr                  #
    # =========================================================#

    @service_method()
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
            self.flush_needed = True
        except OverflowError:
            import warnings
            warnings.warn("Warning: message overflow in fifo_json_log")

    # =========================================================#
    #                     Service Status                      #
    # =========================================================#

    @service_method()
    def get_service_status(self):
        # print("LOGGER SERVER GET STATUS:")
        return self.status

    @service_method()
    def set_service_status(self, status):
        # print("LOGGER SERVER STATUS:", status)
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

    # =========================================================#
    #                Service Time Series Data                 #
    # =========================================================#

    @service_method()
    def get_last_record(self):
        return self.service_time_series_data.get_last_record()

    @service_method()
    def get_average_over(self, from_time, to_time):
        return self.service_time_series_data.get_average_over(
            from_time, to_time
        )

    @service_method()
    def add_pid(self, pid):
        # print("LOGGER SERVER ADD PID", pid)
        self.LPIDs.append(pid)
        self.service_time_series_data.add_pid(pid)

    @service_method()
    def remove_pid(self, pid):
        # print("LOGGER SERVER REMOVE PID", pid)
        try:
            self.LPIDs.pop(pid)
        except IndexError:
            pass
        try:
            self.service_time_series_data.remove_pid(pid)
        except KeyError:
            pass
        try:
            del self.DMethodStats[pid]
        except KeyError:
            pass

    @service_method()
    def start_collecting(self):
        self.service_time_series_data.start_collecting()

    @service_method()
    def stop_collecting(self):
        self.service_time_series_data.stop_collecting()
