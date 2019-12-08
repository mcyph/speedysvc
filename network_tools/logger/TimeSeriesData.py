from struct import Struct
from time import time, sleep
from collections import deque
from abc import ABC, abstractmethod
from os.path import getsize, exists
from _thread import allocate_lock, start_new_thread


# OPEN ISSUE: It might be easier to keep this to stats obtained by psutil,
# so as to not require communication with the child processes?
# I'm not sure how useful that data is actually likely to be


class TimeSeriesData(ABC):
    def __init__(self, path, LFormat,
                 fifo_cache_len=100,
                 sample_interval_secs=5):
        """
        A base class for binary-backed time series data.
        The first item for each "entry" is the unix timestamp
        from the epoch in seconds.

        Note that subclasses define the metadata
        (i.e. how to read the data/which fields there are)
        and so if LFormat changes, then the file will not be readable.
        For this reason, it's probably best to create new subclasses
        rather than modify existing ones, if backwards compabitibility
        is desired.

        :param path: where to put the binary data on-disk
        :param LFormat: a tuple/list of ((struct format, property name), ...).
                        struct format is one of the values at
                        https://docs.python.org/3/library/struct.html,
                        and the property name is something unique/descriptive,
                        e.g. 'io_reads'
        """
        self.LFormat = LFormat
        self.fifo_cache_len = fifo_cache_len
        self.sample_interval_secs = sample_interval_secs

        # Start off with a timestamp, down to the second
        # (4 bytes as in Unix seconds since epoch)
        LOut = ['!I']
        for typecode, name in LFormat:
            LOut.append(typecode)
        self.struct = Struct(''.join(LOut))

        # Get the number of items in the file (if it was previously written to)
        self.deque = deque(maxlen=fifo_cache_len)
        if exists(path):
            assert getsize(path) % self.struct.size == 0
            self.__size = getsize(path)/self.struct.size

            for x, DProperties in self.iterate_backwards():
                self.deque.appendleft(DProperties)
                if x >= fifo_cache_len:
                    break
        else:
            self.__size = 0

        # Fill the rest of the FIFO cache with blank values
        for i in range(fifo_cache_len - len(self.deque)):
            self.deque.appendleft({
                property: 0
                for _, property in LFormat
            })

        self.lock = allocate_lock()
        self.f = open(path, 'ab+')
        start_new_thread(self.__sample_data_loop, ())

    #=========================================================================#
    #                            Recording of Data                            #
    #=========================================================================#

    def __sample_data_loop(self):
        while True:
            try:
                DSample = self.sample_data()
                self.__add_sample(**DSample)
            except:
                import traceback
                traceback.print_exc()

            sleep(self.sample_interval_secs)

    @abstractmethod
    def sample_data(self):
        """
        Must be implemented by subclasses
        :return: a dictionary with all of the keys provided in LFormat
        """
        pass

    def __add_sample(self, **items):
        """
        Add to both the limited in-memory samples, and write them to disk
        :param items:
        :return:
        """
        for key in items:
            assert key in [i[1] for i in self.LFormat], key

        encoded = self.struct.pack(*(
            [time()] +
            [items[name] for _, name in self.LFormat]
        ))

        self.deque.appendleft(items.copy())

        with self.lock:
            self.f.seek(0, 2) # Seek to end of file
            self.f.write(encoded)
            self.__size += 1

    #=========================================================================#
    #                      Retrieval of Data From Disk                        #
    #=========================================================================#

    def __len__(self):
        """
        Get total number of entries
        :return: Get the total number of entries as an int
        """
        return self.__size

    def __getitem__(self, item):
        """
        Get a specific time series data item
        :param item: the index (not the timestamp) relative to the first item
        :return: a dict
        """
        # OPEN ISSUE: Should this support slices??? =================================================================

        with self.lock:
            self.f.seek(item*self.struct.size)
            encoded = self.f.read(self.struct.size)
        data = self.struct.unpack(encoded)

        return dict(zip(
            data, ['timestamp']+[i[1] for i in self.LFormat]
        ))

    def __iter__(self):
        for i in self.iterate_forwards():
            yield i

    def iterate_forwards(self):
        """
        Simply iterate thru using the __getitem__ method
        from the first to the last entry.
        """
        for x in range(len(self)):
            yield self[x]

    def iterate_backwards(self):
        """
        TODO: Seek in chunks of say 256 items each, so as to
        allow for faster reading in the reverse direction
        """
        x = len(self)
        AMOUNT_TO_GET = 256

        while x > 0:
            x -= AMOUNT_TO_GET
            if x < 0:
                x = 0

            LYield = []
            for y in range(x, min(x+AMOUNT_TO_GET, len(self))):
                LYield.append(self[y])
            for i in LYield[::-1]:
                yield i

    def select_range(self, from_time, to_time):
        """

        :param from_time:
        :param to_time:
        :return:
        """

        # TODO: Use a bisect algorithm!!! ===========================================================================

        for DRecord in self:
            if from_time <= DRecord['timestamp'] <= to_time:
                yield DRecord

    def get_average_over(self, from_time, to_time, property):
        """
        Get an average of all recent values - a single value.
        May not make sense for all kinds of data.
        NOTE: This raises a DivideByZeroError if there isn't any values collected!

        :param from_time: the number of seconds since the epoch, as in unix timestamps
        :param to_time: the number of seconds since the epoch, as in unix timestamps
        :param property: The name of the property, as in LFormat
        :return: an integer
        """
        val = 0
        num_vals = 0
        for DRecord in self.select_range(from_time, to_time):
            val += DRecord[property]
        return val / num_vals

    #=========================================================================#
    #                  Short-term In-Memory Data Processing                   #
    #=========================================================================#

    def get_recent_values(self, reversed=True):
        """
        Get a list of the most recent values. By default in reversed order,
        so as to allow for graphs displayed from right to left.

        :param reversed: True/False
        :return: a list of the most recent values, of length self.fifo_cache_len
        """
        if reversed:
            return list(self.deque)[::-1]
        else:
            return list(self.deque)[::]

    def get_recent_average(self, property):
        """
        Get an average of all recent values - a single value.
        May not make sense for all kinds of data.
        NOTE: This raises a DivideByZeroError if there isn't any values collected!

        :param property: The name of the property, as in LFormat
        :return: an integer
        """
        val = 0
        num_vals = 0
        for DRecord in self.deque:
            val += DRecord[property]
        return val / num_vals
