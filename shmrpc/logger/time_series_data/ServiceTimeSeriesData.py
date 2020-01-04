from collections import Counter
from psutil import Process, pid_exists
from shmrpc.logger.time_series_data.TimeSeriesData import TimeSeriesData


class ServiceTimeSeriesData(TimeSeriesData):
    path_suffix = 'procdata'

    def __init__(self, path,
                 fifo_cache_len=300,
                 sample_interval_secs=5,
                 start_collecting_immediately=False):
        """
        A logger for (generic) information to do with processes.

        :param path:
        :param fifo_cache_len:
        :param sample_interval_secs:
        """

        # TODO: What happens when a process terminates abnormally???
        self.last_read_bytes = 0
        self.last_write_bytes = 0
        self.SPIDs = set()
        self.DProcesses = {}

        LFormat = (
            # ('I', 'num_successful_reqs'),
            # ('I', 'num_failed_reqs'),

            ('H', 'num_processes'),

            ('f', 'physical_mem'),
            ('f', 'shared_mem'),
            ('f', 'virtual_mem'),

            ('I', 'io_read'),
            ('I', 'io_written'),

            ('H', 'cpu_usage_pc'),
        )
        TimeSeriesData.__init__(
            self, path, LFormat,
            fifo_cache_len, sample_interval_secs,
            start_collecting_immediately
        )

    def sample_data(self):
        if not self.SPIDs:
            return None

        D = Counter()
        D['num_processes'] = len(self.SPIDs)
        for proc in self.iter_processes():
            D.update(self.__get_cpu_info(proc))
            D.update(self.__get_disk_info(proc))
            D.update(self.__get_mem_info(proc))
        return D

    #===========================================================#
    #              Process Information Management               #
    #===========================================================#

    def add_pid(self, pid):
        self.SPIDs.add(pid)

    def remove_pid(self, pid):
        self.SPIDs.remove(pid)

    def get_process(self, pid):
        if not pid in self.DProcesses:
            self.DProcesses[pid] = Process(pid)
        return self.DProcesses[pid]

    def iter_processes(self):
        for pid in list(self.SPIDs):
            if not pid_exists(pid):
                self.remove_pid(pid)
                continue

            try:
                p = self.get_process(pid)
            except:
                import traceback
                traceback.print_exc()
                continue

            yield p

    #===========================================================#
    #                    CPU/Mem/Disk Info                      #
    #===========================================================#

    def __get_cpu_info(self, proc):
        return {
            'cpu_usage_pc': int(proc.cpu_percent())
        }

    def __get_mem_info(self, proc):
        mem_info = proc.memory_full_info()

        return {
            'shared_mem': mem_info.shared, # TODO: Make this check for shared memory between like processes?
            'physical_mem': mem_info.rss,
            'virtual_mem': mem_info.vms # TODO: Make this not include physical memory???
        }

    def __get_disk_info(self, proc):
        # Note: read_bytes/write_bytes differ from read_chars/write_chars, in that
        # only bytes actually read/written to disk will be included in the amounts.
        # I think for this purpose this is the most appropriate stat, as there's
        # probably a lot of io ops done in shared memory.

        io_counters = proc.io_counters()
        read_bytes = io_counters.read_bytes
        write_bytes = io_counters.write_bytes
        D = {
            'io_read': read_bytes-self.last_read_bytes,
            'io_written': write_bytes-self.last_write_bytes,
        }
        self.last_read_bytes = read_bytes
        self.last_write_bytes = write_bytes
        return D
