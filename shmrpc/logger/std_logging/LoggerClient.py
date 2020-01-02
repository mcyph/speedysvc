import sys
import time
from os import getpid
from queue import Queue
from _thread import allocate_lock, start_new_thread

from shmrpc.logger.LoggerServer import LoggerServer
from shmrpc.rpc.shared_memory.SHMClient import SHMClient
from shmrpc.rpc.base_classes.ClientMethodsBase import ClientMethodsBase
from shmrpc.logger.std_logging.log_entry_types import \
    NOTSET, DEBUG, INFO, ERROR, WARN, CRITICAL


# We'll use a queue here sending in a thread rather
# than synchronous logging, so as to minimise the
# risk of recursive log writes, etc
log_queue = Queue()


class LoggerClient(ClientMethodsBase):
    def __init__(self, server_methods):
        """
        A basic logger which sends stderr/stdout
        output to a logging server
        """
        self.lock = allocate_lock()
        self.__pid = getpid()

        self.client = SHMClient(LoggerServer, port=f'{server_methods.port}_log')
        ClientMethodsBase.__init__(self, client_provider=self.client)
        self.stderr_logger = self._StdErrLogger(self)
        self.stdout_logger = self._StdOutLogger(self)
        start_new_thread(self.__log_thread, ())

    #=================================================================#
    #                           RPC Methods                           #
    #=================================================================#

    def __log_thread(self):
        while True:
            try:
                self._write_to_log_(log_queue.get())
            except:
                # WARNING WARNING#
                # Trouble is, if things go wrong here, they could lead to recursive
                # write to stderr/stdout, so I'm not sure handling this is worth it..
                time.sleep(1)

    def _loaded_ok_signal_(self):
        """
        Signify to the logger server that
        the server has started properly
        """
        self.send(LoggerServer._loaded_ok_signal_, [])

    def _write_to_log_(self, log_params):
        """
        Should not be called directly!
        :param log_params:
        :return:
        """
        self.send(LoggerServer.stdout_write, log_params)

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
        pid = self.__pid
        port = self.server_methods.port
        service_name = self.server_methods.name

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
        self(msg, WARN)
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
            self.old_stdout = sys.stdout
            sys.stdout = self
            self.logger_client = logger_client

        def write(self, s):
            # WARNING: If the logger client's send command needs
            # to send to the log itself, then it'll result in a deadlock!
            # This is the reason why I'm replacing sys.stdout during the call..
            self.old_stdout.write(s)
            self.logger_client(s, NOTSET)

    class _StdErrLogger:
        def __init__(self, logger_client):
            self.old_stderr = sys.stderr
            sys.stderr = self
            self.logger_client = logger_client

        def write(self, s):
            self.old_stderr.write(s)
            self.logger_client(s, ERROR)
