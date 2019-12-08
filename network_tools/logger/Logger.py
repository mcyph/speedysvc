from _thread import allocate_lock
from network_tools.rpc.posix_shm_sockets.SHMServer import SHMServer
from network_tools.rpc_decorators import raw_method, json_method


class LoggerServer:
    def __init__(self, log_dir, server_methods):
        """

        :param log_dir:
        :param server_methods:
        """

        # NOTE ME: I'm overriding the port so as to not have a
        #          collision with the existing (integer) port,
        #          used by the original server.
        self.port = f'{server_methods.port}_log'
        self.name = f'{server_methods.name}_log'
        self.shm_server = SHMServer(self)

        # Store the single value stats
        # (e.g. how long each individual call takes,
        # and how many times each call has taken place)
        # which would take too long to store separately
        self.DAveragesByProcessID = {}

        # Open the stdout/stderr files
        self.stdout_lock = allocate_lock()
        self.f_stdout = open(
            f'{log_dir}/{self.name}.stdout', 'a+',
            errors='replace', encoding='utf-8'
        ) # binary??
        self.stderr_lock = allocate_lock()
        self.f_stderr = open(
            f'{log_dir}/{self.name}.stderr', 'a+',
            errors='replace', encoding='utf-8'
        )

    @raw_method
    def stderr_write(self, s):
        """
        Write to stderr
        :param s:
        :return:
        """
        with self.stdout_lock:
            self.f_stdout.write(s)

    @raw_method
    def stdout_write(self, s):
        """
        Write to stdout
        :param s:
        :return:
        """
        with self.stderr_lock:
            self.f_stderr.write(s)

    @json_method
    def get_averages(self, process_id):
        """
        TODO: Get the previously saved averages
              from disk, and return them (if they exist),
              otherwise None.

        :param process_id:
        :return:
        """

    @json_method
    def update_averages(self, process_id, DAverages):
        """
        TODO: Allow logging of:

        Per process, combined together:
        * Number of calls overall
        * Average time calls take overall

        Saved in JSON, so as to allow saving of a simple
        set of variables in human-readable format.

        (I can't think of a good reason to log individual
         calls as datapoints - in fact it might make things
         unacceptably slow.)
        """

        # Verify the methods in DAverages correspond to
        # methods which I've been provided
        LKeys = list(DAverages)
        for key in LKeys:
            pass

        for key in FIXME(self.server_provider):
            pass

        self.DAveragesByProcessID[process_id] = DAverages

    @json_method
    def log_stats(self, DStats):
        """
        TODO: Allow logging of:

        Across all processes:
        * Current number of processes
        * Memory usage
        * CPU usage (pc CPU/num processes - will always be out of 100)
        * IO usage

        :param DStats:
        :return:
        """
        pass
