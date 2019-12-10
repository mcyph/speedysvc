import sys
from network_tools.logger.LoggerServer import LoggerServer
from network_tools.rpc.shared_memory.SHMClient import SHMClient
from network_tools.rpc.base_classes.ClientMethodsBase import ClientMethodsBase


class LoggerClient(ClientMethodsBase):
    def __init__(self, server_methods):
        """
        A basic logger which sends stderr/stdout
        output to a logging server
        """
        self.client = SHMClient(LoggerServer, port=f'{server_methods.port}_log')
        self.stdout_logger = _StdOutLogger(self)
        self.stderr_logger = _StdErrLogger(self)
        ClientMethodsBase.__init__(self, client_provider=self.client)

    def stdout_write(self, s):
        if not isinstance(s, (str, bytes)):
            s = repr(s)
        if isinstance(s, str):
            s = s.encode('utf-8')
        self.send(LoggerServer.stdout_write, s)

    def stderr_write(self, s):
        if not isinstance(s, (str, bytes)):
            s = repr(s)
        if isinstance(s, str):
            s = s.encode('utf-8')
        self.send(LoggerServer.stderr_write, s)


class _StdOutLogger:
    def __init__(self, logger_client):
        self.old_stdout = sys.stdout
        sys.stdout = self
        self.logger_client = logger_client

    def write(self, s):
        self.old_stdout.write(s)
        self.logger_client.stdout_write(s)


class _StdErrLogger:
    def __init__(self, logger_client):
        self.old_stderr = sys.stderr
        sys.stderr = self
        self.logger_client = logger_client

    def write(self, s):
        self.old_stderr.write(s)
        self.logger_client.stderr_write(s)
