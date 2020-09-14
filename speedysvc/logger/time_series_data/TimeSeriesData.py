from struct import Struct
from time import time, sleep
from collections import deque, Counter
from abc import ABC, abstractmethod
from os.path import getsize, exists
from _thread import allocate_lock, start_new_thread


# OPEN ISSUE: It might be easier to keep this to stats obtained by psutil,
# so as to not require communication with the child processes?
# I'm not sure how useful that data is actually likely to be


SAMPLE_INTERVAL_SECS = 5


_sample_loop_started = [False]
_LTimeSeriesData = []
def _time_series_loop():
    """
    Monitor time series data in a
    single thread to minimize resources
    """
    while True:
        for tsd in _LTimeSeriesData[:]:
            try:
                tsd.sample_data_loop()
            except:
                import traceback
                traceback.print_exc()
        sleep(SAMPLE_INTERVAL_SECS)


class TimeSeriesData(ABC):
    def __init__(self, LFormat,
                 fifo_cache_len=300,
                 sample_interval_secs=5,
                 start_collecting_immediately=False):
        """
        A base class for binary-backed time series data.
        The first item for each "entry" is the unix timestamp
        from the epoch in seconds.

        Note that subclasses define the metadata
        (i.e. how to read the data/which fields there are)
        and so if LFormat changes, then the file will not be readable.
        For this reason, it's probably best to create new subclasses
        rather than modify existing ones, if backwards compatibility
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

        self.lock = allocate_lock()

        # Start off with a timestamp, down to the second
        # (4 bytes as in Unix seconds since epoch)
        LOut = ['!I']
        for typecode, name in LFormat:
            LOut.append(typecode)
        self.struct = Struct(''.join(LOut))

        # Get the number of items in the file (if it was previously written to)
        self.deque = deque(maxlen=fifo_cache_len)

        # Fill the rest of the FIFO cache with blank values
        for i in range(fifo_cache_len - len(self.deque)):
            # CHECK ME!!! ===========================================================================================
            # This might throw off the averages!!
            self.deque.appendleft({
                property: 0
                for _, property in [(None, 'timestamp')]+list(LFormat)
            })

        _LTimeSeriesData.append(self)
        self.collecting_data = False
        if start_collecting_immediately:
            self.start_collecting()

    def start_collecting(self):
        """
        Start the collection of data
        """
        if self.collecting_data:
            # Can't start collection if already are
            # Best to raise an exception explicitly here,
            # as could indicate start_collecting_immediately
            # was mistakenly set, etc
            raise Exception("Collection of data already started")

        if not _sample_loop_started[0]:
            _sample_loop_started[0] = True
            start_new_thread(_time_series_loop, ())

        self.collecting_data = True

    def stop_collecting(self):
        """
        Pause the collection of data
        """
        if not self.collecting_data:
            raise Exception("Not currently collecting data")
        self.collecting_data = False

    #=========================================================================#
    #                            Recording of Data                            #
    #=========================================================================#

    def sample_data_loop(self):
        if self.collecting_data:
            try:
                DSample = self.sample_data()
                if DSample: # WARNING!!! ======================================
                    self.__add_sample(**DSample)
            except:
                pass
                #import traceback
                #traceback.print_exc()

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

        items = items.copy()
        items['timestamp'] = int(time())
        self.deque.appendleft(items)

    #=========================================================================#
    #                      Retrieval of Data From Disk                        #
    #=========================================================================#

    def __len__(self):
        """
        Get total number of entries
        :return: Get the total number of entries as an int
        """
        return len(self.deque)

    def __getitem__(self, item):
        """
        Get a specific time series data item
        :param item: the index (not the timestamp)
                     relative to the first item
        :return: a dict
        """
        return self.deque[item]

    def __iter__(self):
        with self.lock:
            for i in self.iterate_forwards():
                yield i

    def iterate_forwards(self):
        """
        Simply iterate thru using the __getitem__ method
        from the first to the last entry.
        """
        for x in range(len(self)-1, -1, -1):
            yield self[x]

    def iterate_backwards(self):
        for x in range(len(self)):
            yield self[x]

    def select_range(self, from_time, to_time):
        """
        Get statistics over a specified time range.
        :param from_time: the number of seconds since
                          the epoch, as in unix timestamps
        :param to_time: the number of seconds since
                        the epoch, as in unix timestamps
        """

        # TODO: Use a bisect algorithm/store seek positions for certain
        # timestamps to prevent having to go thru every single record!!! ===========================================================================

        for DRecord in self:
            if from_time <= DRecord['timestamp'] <= to_time:
                yield DRecord

    def get_average_over(self, from_time, to_time):
        """
        Get an average of all recent values - a single value.
        May not make sense for all kinds of data.
        NOTE: This raises a DivideByZeroError if
              there aren't any values collected!

        :param from_time: the number of seconds since
                          the epoch, as in unix timestamps
        :param to_time: the number of seconds since the epoch,
                        as in unix timestamps
        :return: an integer
        """
        DVals = Counter()
        num_vals = 0

        with self.lock:
            for DRecord in self.deque:
                if from_time <= DRecord['timestamp'] <= to_time:
                    for property in DRecord:
                        if property == 'timestamp':
                            continue
                        DVals[property] += DRecord[property]
                    num_vals += 1

        return {
            key: val / num_vals
            for key, val
            in DVals.items()
        }

    #=========================================================================#
    #                  Short-term In-Memory Data Processing                   #
    #=========================================================================#

    def get_last_record(self):
        """

        :return:
        """
        return self.deque[0]

    def get_recent_values(self, reversed=True):
        """
        Get a list of the most recent values.
        By default in reversed order, so as to allow
        for graphs displayed from right to left.

        :param reversed: True/False
        :return: a list of the most recent values,
                 of length self.fifo_cache_len
        """
        if reversed:
            return list(self.deque)[::-1]
        else:
            return list(self.deque)[::]

    def get_recent_average(self, property):
        """
        Get an average of all recent values -
        a single value.
        May not make sense for all kinds of data.
        NOTE: This raises a DivideByZeroError if
              there aren't any values collected!

        :param property: The name of the property,
                         as in LFormat
        :return: an integer
        """
        val = 0
        num_vals = 0

        with self.lock:
            for DRecord in self.deque:
                val += DRecord[property]

        return val / num_vals
