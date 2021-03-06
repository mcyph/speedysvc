import sys
import time
from os import getpid
from queue import Queue, Empty
import traceback
from _thread import allocate_lock, start_new_thread

from speedysvc.logger.std_logging.LoggerServer import LoggerServer
from speedysvc.client_server.shared_memory.SHMClient import SHMClient
from speedysvc.client_server.base_classes.ClientMethodsBase import ClientMethodsBase
from speedysvc.logger.std_logging.log_entry_types import \
    NOTSET, DEBUG, INFO, ERROR, WARNING, CRITICAL, STDOUT, STDERR


# We'll use a queue here sending in a thread rather
# than synchronous logging, so as to minimise the
# risk of recursive log writes, etc
log_queue = Queue()


_old_stdout = sys.stdout
_old_stderr = sys.stderr


class LoggerClient(ClientMethodsBase):
    def __init__(self, service_server_methods):
        """
        A basic logger which sends stderr/stdout
        output to a logging server
        """
        self.lock = allocate_lock()
        self.pid = getpid()
        # Note that ClientMethodsBase will have a set of server methods
        # associated with the log service. These are the server methods
        # associated with the service itself.
        self.service_server_methods = service_server_methods

        self.client = SHMClient(LoggerServer, port=f'{service_server_methods.port}_log',
                                use_spinlock=False, use_in_process_lock=True)
        ClientMethodsBase.__init__(self, client_provider=self.client)
        self.stderr_logger = self._StdErrLogger(self)
        self.stdout_logger = self._StdOutLogger(self)
        self.__shut_me_down = False
        start_new_thread(self.__log_thread, ())

    def shutdown(self):
        self.__shut_me_down = True

    #=================================================================#
    #                           RPC Methods                           #
    #=================================================================#

    def __log_thread(self):
        """
        A lot of the time, it can be hard to know where stderr/stdout starts and ends
        (e.g. print('foo', 'bar') might print foo, bar, and \n separately)

        This tries to treat stdout/stderr data as a sequence of directly following
        strings and merges it together, assuming they occur almost immediately after
        each other (up to 0.01 seconds).

        I've made stdout/stderr output as [INFO/ERROR]+9 level
        """
        cur_stderr_msg = None
        cur_stdout_msg = None
        method_stats_last_updated = 0

        while not self.__shut_me_down:
            try:
                if cur_stderr_msg or cur_stdout_msg:
                    item = log_queue.get(timeout=0.01)
                else:
                    item = log_queue.get(timeout=2.0)

                if item[-1] == STDOUT:
                    if cur_stdout_msg:
                        # Append to the previous stdout call
                        cur_stdout_msg[-2] += item[-2]
                    else:
                        cur_stdout_msg = list(item)
                elif item[-1] == STDERR:
                    if cur_stderr_msg:
                        # Append to the previous stderr call
                        cur_stderr_msg[-2] += item[-2]
                    else:
                        cur_stderr_msg = list(item)
                else:
                    self._write_to_log_(item)

            except Empty:
                if cur_stdout_msg:
                    # If Empty is raised, a timeout has occurred
                    # Assume this is the end of the data that's being sent to stdout
                    self._write_to_log_(tuple(cur_stdout_msg[:-1]+[INFO+9]))
                    cur_stdout_msg = None

                if cur_stderr_msg:
                    # The same, but for stderr
                    self._write_to_log_(tuple(cur_stderr_msg[:-1]+[ERROR+9]))
                    cur_stderr_msg = None

                if time.time()-method_stats_last_updated >= 4:
                    # Periodically inform the management server how long methods
                    # are taking/how many times they're being called for benchmarks
                    self._update_method_stats_()
                    method_stats_last_updated = time.time()

                elif not cur_stderr_msg and not cur_stderr_msg and sys.platform == 'win32':
                    # win32 doesn't seem to allow for timeouts with the queue here
                    time.sleep(2.0)

            except Exception as e:
                # WARNING WARNING - should (hopefully) never get here
                # I'm printing errors directly to the old stderr
                # to prevent the risk of recursive exceptions
                import traceback
                _old_stderr.write(traceback.format_exc())
                time.sleep(1)

    def _write_to_log_(self, log_params):
        """
        Should not be called directly!
        :param log_params:
        :return:
        """
        self.send(LoggerServer._write_to_log_, log_params)

    def _update_method_stats_(self):
        """
        Send method statistics to the central management
        interface to allow for benchmarks periodically
        """
        DStats = {}

        for name in dir(self.service_server_methods):
            attr = getattr(self.service_server_methods, name)
            if hasattr(attr, 'metadata'):
                # DMetadata = {'num_calls': ..., 'total_time': ...}
                DStats[name] = attr.metadata

        self.send(LoggerServer._update_method_stats_, [self.pid, DStats])

    #=========================================================#
    #                     Service Status                      #
    #=========================================================#

    def get_service_status(self):
        return self.send(LoggerServer.get_service_status, [])

    def set_service_status(self, status):
        return self.send(LoggerServer.set_service_status, [status])

    #=========================================================#
    #                Service Time Series Data                 #
    #=========================================================#

    def get_last_record(self):
        return self.send(LoggerServer.get_last_record, [])

    def get_average_over(self, from_time, to_time):
        return self.send(LoggerServer.get_average_over, [from_time, to_time])

    def add_pid(self, pid):
        return self.send(LoggerServer.add_pid, [pid])

    def remove_pid(self, pid):
        return self.send(LoggerServer.remove_pid, [pid])

    def start_collecting(self):
        return self.send(LoggerServer.start_collecting, [])

    def stop_collecting(self):
        return self.send(LoggerServer.stop_collecting, [])

    #=================================================================#
    #                      User-Callable Methods                      #
    #=================================================================#

    def __call__(self, msg, level=NOTSET):
        """
        Output a message. This allows going self.log()
        as shorthand for self.log.notset(msg)

        Note this puts onto a log queue running in a different thread,
        so as to prevent potential deadlocks when one thread tries to
        write at the same time

        :param msg: the string message
        :param level: the log level, e.g. DEBUG or INFO
        """
        pid = self.pid

        #print(hasattr(self, 'server_methods'))

        if hasattr(self.service_server_methods, 'port'):
            port = self.service_server_methods.port
        else:
            port = -1

        if hasattr(self.service_server_methods, 'name'):
            service_name = self.service_server_methods.name
        else:
            service_name = '(unknown service)'

        log_queue.put(
            (int(time.time()), pid, port, service_name, msg, level)
        )

    def notset(self, msg):
        """
        Output a message of whose level is not defined
        :param msg: the string message
        """
        self(msg, NOTSET)

    def debug(self, msg):
        """
        Output a debug message
        :param msg: the string message
        """
        self(msg, DEBUG)

    def info(self, msg):
        """
        Output an informational message
        :param msg: the string message
        """
        self(msg, INFO)
    information = info

    def error(self, msg):
        """
        Output an error message
        :param msg: the string message
        """
        self(msg, ERROR)

    def warn(self, msg):
        """
        Output a warning message
        :param msg: the string message
        """
        self(msg, WARNING)
    warning = warn

    def critical(self, msg):
        """
        Output a critical/fatal message
        :param msg: the string message
        """
        self(msg, CRITICAL)

    #=================================================================#
    #            StdOut/StdErr Backwards Compatibility                #
    #=================================================================#

    class _StdOutLogger:
        def __init__(self, logger_client):
            sys.stdout = self
            self.logger_client = logger_client

        def flush(self):
            _old_stdout.flush()

        def write(self, s):
            _old_stdout.write(s)
            self.logger_client(s, STDOUT)

    class _StdErrLogger:
        def __init__(self, logger_client):
            sys.stderr = self
            self.logger_client = logger_client

        def flush(self):
            _old_stderr.flush()

        def write(self, s):
            _old_stderr.write(s)
            self.logger_client(s, STDERR)

