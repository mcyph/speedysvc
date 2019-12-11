import sys
import time
from queue import Queue
from _thread import allocate_lock, start_new_thread
from network_tools.logger.LoggerServer import LoggerServer
from network_tools.rpc.shared_memory.SHMClient import SHMClient
from network_tools.rpc.base_classes.ClientMethodsBase import ClientMethodsBase


# We'll use a queue here sending in a thread rather
# than synchronous logging, so as to minimise the
# risk of recursive log writes, etc
log_queue = Queue()
STDOUT = 0
STDERR = 1


class LoggerClient(ClientMethodsBase):
    def __init__(self, server_methods):
        """
        A basic logger which sends stderr/stdout
        output to a logging server
        """
        self.lock = allocate_lock()

        self.client = SHMClient(LoggerServer, port=f'{server_methods.port}_log')
        ClientMethodsBase.__init__(self, client_provider=self.client)
        self.stderr_logger = _StdErrLogger(self)
        self.stdout_logger = _StdOutLogger(self)
        start_new_thread(self.__log_thread, ())

    def __log_thread(self):
        while True:
            try:
                typ, msg = log_queue.get()
                if typ == STDOUT:
                    self.stdout_write(msg)
                elif typ == STDERR:
                    self.stderr_write(msg)
                else:
                    raise Exception("Unknown queue type %s" % typ)
            except:
                # WARNING WARNING#
                # Trouble is, if things go wrong here, they could lead to recursive
                # write to stderr/stdout, so I'm not sure handling this is worth it..
                time.sleep(1)

    def loaded_ok_signal(self):
        """
        Signify to the logger server that
        the server has started properly
        """
        self.send(LoggerServer.loaded_ok_signal, [])

    def stdout_write(self, s):
        if not isinstance(s, (str, bytes)):
            s = repr(s)
        if isinstance(s, str):
            s = s.encode('utf-8')
        assert self.send(LoggerServer.stdout_write, s) == b'ok'

    def stderr_write(self, s):
        if not isinstance(s, (str, bytes)):
            s = repr(s)
        if isinstance(s, str):
            s = s.encode('utf-8')
        assert self.send(LoggerServer.stderr_write, s) == b'ok'


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
        log_queue.put((STDOUT, s))


class _StdErrLogger:
    def __init__(self, logger_client):
        self.old_stderr = sys.stderr
        sys.stderr = self
        self.logger_client = logger_client

    def write(self, s):
        self.old_stderr.write(s)
        log_queue.put((STDERR, s))
