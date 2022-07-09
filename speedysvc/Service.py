from typing import Optional

class Service:
    def __init__(self,
                 service_name: str,
                 port: int,
                 server_module: str,
                 client_module: Optional[str] = None,
                 host: Optional[str] = None,   # TODO: Check the name of this arg!!
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

        self.__args = {
            'service_name': service_name,
            'port': port,
            'server_module': server_module,
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

    def get_tcp_bind(self):
        return self.__args['host']

    def get_service_name(self):
        return self.__args['service_name']

    def get_port(self):
        return self.__args['port']

    def get_logger_server(self):
        return self.logger_server

    @lock_fn
    def start(self):
        # print("SECTION:", section)
        assert not self.started, \
            f"Service {self.__args['service_name']}:{self.__args['port']} has already been started!"

        self.__run_multi_proc_server(
            server_methods, **self.__args,
            fifo_json_log_parent=self.fifo_json_log_parent
        )

    @lock_fn
    def stop(self):
        assert self.started, \
            f"Service {self.__args['service_name']}:{self.__args['port']} can't be stopped if it hasn't been started!"

        self.logger_server.set_service_status('stopping')
        proc = self.DProcByPort[port]
        self.logger_server.stop_collecting()
        self.__kill_proc(proc)
        self.logger_server.set_service_status('stopped')

    def __kill_proc(self, proc):
        kill_pid_and_children(self.proc.pid)
        self.proc = None

    @lock_fn
    def run(self):
        print(f"Starting service {self.__args['service_name']}:", end=" ")

        # Create the logger server, which allows
        # the services to communicate back with us
        make_dirs(f"{self.log_dir}/{self.__args['service_name']}")

        if not self.logger_server:
            # Create a logger server for each service, persistent to this process
            # This makes it so we can restart services
            # While it would be nice to restart the logger too,
            # currently that'd require a fair amount of refactoring
            logger_server = LoggerServer(log_dir=f"{self.__args['log_dir']}/{self.__args['service_name']}/",
                                         server_methods=self.server_methods,
                                         fifo_json_log_parent=self.fifo_json_log_parent)
            self.logger_server = logger_server

        logger_server = self.DLoggerServersByPort[self.__args['port']]
        logger_server.set_service_status('forking')

        # Assemble relevant parameters
        environ = os.environ.copy()
        environ["PATH"] = "/usr/sbin:/sbin:" + environ["PATH"]
        proc = self.proc = subprocess.Popen([
            sys.executable, '-m',
            'speedysvc.client_server.shared_memory.MultiProcessManager',
            json.dumps(self.__args)
        ], env=environ)

        logger_server.proc = proc  # HACK!
        logger_server.host = self.host  # HACK!

        if wait_until_completed:
            while logger_server.get_service_status() != 'started':
                time.sleep(0.1)

        print('[OK]')
