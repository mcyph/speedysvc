import sys
from network_tools.logger.Logger import LoggerServer
from network_tools.rpc.shared_memory.SHMClient import SHMClient


class LoggerClient:
    def __init__(self):
        self.shm_server = SHMClient(LoggerServer)
        self.stdout_logger = _StdOutLogger(self)
        self.stderr_logger = _StdErrLogger(self)

    def stderr_write(self, s):
        if isinstance(s, str):
            s = s.encode('utf-8')
        self.shm_server.send('stderr_write', s)

    def stderr_read(self, s):
        if isinstance(s, str):
            s = s.encode('utf-8')
        self.shm_server.send('stderr_read', s)


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
