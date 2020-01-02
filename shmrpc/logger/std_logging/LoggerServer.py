import time
from _thread import allocate_lock, start_new_thread
from shmrpc.rpc.shared_memory.SHMServer import SHMServer
from shmrpc.rpc_decorators import raw_method, json_method


FLUSH_EVERY_SECONDS = 1.0


class LoggerServer:
    def __init__(self, log_dir, server_methods):
        """

        :param log_dir:
        :param server_methods:
        """
        self.loaded_ok = False

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
        self.DAveragesByProcessID = {}

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

        # Start the server
        self.shm_server(
            server_methods=self,
            init_resources=True
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
            self.flush_needed = False
        time.sleep(FLUSH_EVERY_SECONDS)

    #=========================================================#
    #                 Write to stdout/stderr                  #
    #=========================================================#

    @raw_method
    def stderr_write(self, s):
        """
        Write to stderr
        :param s:
        :return:
        """
        with self.stderr_lock:
            self.f_stderr.write(s)
            #self.f_stderr.flush()
            self.flush_needed = True
        return b'ok'

    @raw_method
    def stdout_write(self, s):
        """
        Write to stdout
        :param s:
        :return:
        """
        with self.stdout_lock:
            self.f_stdout.write(s)
            #self.f_stdout.flush()
            self.flush_needed = True
        return b'ok'

    @json_method
    def loaded_ok_signal(self):
        self.loaded_ok = True
        return None