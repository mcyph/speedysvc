import os
import sys
import time
import json
import subprocess
from threading import Lock
from typing import Optional

from speedysvc.toolkit.io.make_dirs import make_dirs
from speedysvc.logger.std_logging.LoggerServer import LoggerServer
from speedysvc.toolkit.kill_pid_and_children import kill_pid_and_children


def lock_fn(fn):
    def new_fn(self, *args, **kw):
        with self.lock:
            return fn(self, *args, **kw)
    return new_fn


class Service:
    def __init__(self,
                 service_name: str,
                 service_port: int,
                 server_module: str,
                 service_class_name: str,
                 client_module: Optional[str] = None,
                 host: Optional[str] = None,
                 tcp_allow_insecure_serialisation: bool = False,

                 max_proc_num: int = 1,
                 min_proc_num: int = 1,
                 max_proc_mem_bytes: Optional[int] = None,
                 wait_until_completed: bool = False,

                 new_proc_cpu_pc: float = 0.3,
                 new_proc_avg_over_secs: float = 20,
                 kill_proc_avg_over_secs: float = 240,

                 log_dir: str = '/tmp',
                 fifo_json_log_parent = None):

        self.lock = Lock()
        self.__args = {
            'service_name': service_name,
            'service_port': service_port,
            'server_module': server_module,
            'service_class_name': service_class_name,
            'client_module': client_module,
            'host': host,
            'tcp_allow_insecure_serialisation': tcp_allow_insecure_serialisation,
            'max_proc_num': max_proc_num,
            'min_proc_num': min_proc_num,
            'max_proc_mem_bytes': max_proc_mem_bytes,
            'wait_until_completed': wait_until_completed,
            'new_proc_cpu_pc': new_proc_cpu_pc,
            'new_proc_avg_over_secs': new_proc_avg_over_secs,
            'kill_proc_avg_over_secs': kill_proc_avg_over_secs,
            'log_dir': log_dir,
            'fifo_json_log_parent': fifo_json_log_parent,
        }

        self.logger_server = None
        self.proc = None
        self.started = False

    def get_tcp_bind(self) -> str:
        return self.__args['host']

    def get_service_name(self) -> str:
        return self.__args['service_name']

    def get_port(self) -> int:
        return self.__args['service_port']

    def get_logger_server(self):
        return self.logger_server

    def get_pid(self) -> int:
        return self.proc.pid

    @lock_fn
    def start(self):
        # print("SECTION:", section)
        assert not self.started, \
            f"Service {self.__args['service_name']}:{self.__args['service_port']} has already been started!"
        self.__run()

    @lock_fn
    def stop(self):
        assert self.started, \
            f"Service {self.__args['service_name']}:{self.__args['service_port']} can't be stopped if it hasn't been started"
        #assert self.logger_server.get_service_status() == 'started', \
        #    f"Service {self.__args['service_name']}:{self.__args['service_port']} can't be stopped if it is in state {self.logger_server.get_service_status()}"

        self.logger_server.set_service_status('stopping')
        self.logger_server.stop_collecting()
        self.__kill_proc()
        self.logger_server.set_service_status('stopped')
        self.started = False

    def __kill_proc(self):
        #print("[SERVICE] Killing proc:", self.proc.pid)
        kill_pid_and_children(self.proc.pid)
        self.proc = None

    def __run(self):
        print(f"Starting service {self.__args['service_name']}:", end=" ")

        # Create the logger server, which allows
        # the services to communicate back with us
        make_dirs(f"{self.__args['log_dir']}/{self.__args['service_name']}")

        if not self.logger_server:
            # Create a logger server for each service, persistent to this process
            # This makes it, so we can restart services
            # While it would be nice to restart the logger too,
            # currently that'd require a fair amount of refactoring
            self.logger_server = LoggerServer(log_dir=f"{self.__args['log_dir']}/{self.__args['service_name']}/",
                                              server_name=self.__args['service_name'],
                                              server_port=self.__args['service_port'],
                                              fifo_json_log_parent=self.__args['fifo_json_log_parent'])

        status = self.logger_server.get_service_status()
        assert status == 'stopped', f"Can't start service as currently in {status} state"

        self.logger_server.set_service_status('forking')

        # Assemble relevant parameters
        environ = os.environ.copy()
        environ["PATH"] = "/usr/sbin:/sbin:" + environ["PATH"]
        proc = self.proc = subprocess.Popen([
            sys.executable, '-m',
            'speedysvc.client_server.MultiProcessManager',
            json.dumps(self.__args)
        ], env=environ)

        self.logger_server.proc = proc  # HACK!
        self.logger_server.host = self.__args['host']  # HACK!

        if self.__args['wait_until_completed']:
            while self.logger_server.get_service_status() != 'started':
                time.sleep(0.1)

        self.started = True
        print('[OK]')