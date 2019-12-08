import sys
from network_tools.logger.Logger import LoggerServer
from network_tools.rpc_implementations.posix_shm_rpc.SHMClient import SHMClient


class LoggerClient:
    def __init__(self):
        self.shm_server = SHMClient(LoggerServer)
        self.stdout_logger = _StdOutLogger(self)
        self.stderr_logger = _StdErrLogger(self)

    def stderr_write(self, s):
        pass

    def stderr_read(self, s):
        pass


class _StdOutLogger:
    def __init__(self, logger_client):
        self.logger_client = logger_client

    def write(self, s):
        self.logger_client.stdout_write(s)


class _StdErrLogger:
    def __init__(self, logger_client):
        self.logger_client = logger_client

    def write(self, s):
        self.logger_client.stderr_write(s)

