from struct import Struct
from time import time, sleep
from collections import deque, Counter
from abc import ABC, abstractmethod
from os.path import getsize, exists
from _thread import allocate_lock, start_new_thread


# OPEN ISSUE: It might be easier to keep this to stats obtained by psutil,
# so as to not require communication with the child processes?
# I'm not sure how useful that data is actually likely to be


class TimeSeriesData(ABC):
    def __init__(self, path, LFormat,
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
        self.f = open(path, 'ab+')

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
            self.__size = int(getsize(path)/self.struct.size)

            # OPEN ISSUE: Start off with blank data in the cache,
            # as that data normally isn't that useful in between sessions.
            # The disadvantage would be __getitem__ wouldn't be cacheable
            LAppend = []
            for x, DProperties in enumerate(self.iterate_backwards()):
                LAppend.append(DProperties)
                if x >= fifo_cache_len:
                    break

            for DProperties in reversed(LAppend):
                # Make sure appended in order oldest first
                self.deque.appendleft(DProperties)
        else:
            self.__size = 0

        # Fill the rest of the FIFO cache with blank values
        for i in range(fifo_cache_len - len(self.deque)):
            # CHECK ME!!! ===========================================================================================
            # This might throw off the averages!!
            self.deque.appendleft({
                property: 0
                for _, property in [(None, 'timestamp')]+list(LFormat)
            })

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
        self.collecting_data = True
        start_new_thread(self.__sample_data_loop, ())

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

    def __sample_data_loop(self):
        while self.collecting_data:
            try:
                DSample = self.sample_data()
                if DSample: # WARNING!!! ======================================
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

        items = items.copy()
        items['timestamp'] = int(time())
        encoded = self.struct.pack(*(
            [items['timestamp']] +
            [items[name] for _, name in self.LFormat]
        ))
        self.deque.appendleft(items)

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
        :param item: the index (not the timestamp)
                     relative to the first item
        :return: a dict
        """
        # OPEN ISSUE: Should this support slices??? =================================================================

        # TODO: GRAB FROM CACHE IF POSSIBLE!!! ======================================================================

        with self.lock:
            self.f.seek(item*self.struct.size)
            encoded = self.f.read(self.struct.size)

            if len(encoded) != self.struct.size:
                # If not enough returned here, it's probably
                # data not written to disk due to OS buffering
                self.f.flush()
                self.f.seek(item * self.struct.size)
                encoded = self.f.read(self.struct.size)
                assert len(encoded) == self.struct.size

        data = self.struct.unpack(encoded)

        return dict(zip(
            ['timestamp'] + [i[1] for i in self.LFormat],
            data
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

        # the last value in self.deque is the least recent
        if from_time >= self.deque[-1]['timestamp']:
            # Use the recent values cache if range in memory
            for DRecord in self.deque:
                if from_time <= DRecord['timestamp'] <= to_time:
                    for property in DRecord:
                        if property == 'timestamp':
                            continue
                        DVals[property] += DRecord[property]
                    num_vals += 1
        elif self.deque:
            # I've disabled the below code grabbing from disk,
            # as should always have enough data in cache
            # (at least in the current interface).
            # If I ever need to do long-term analytics,
            # will uncomment the below.
            raise Exception(f"Averaging should always be in memory! (from_time: {from_time}; last deque: {self.deque[-1]}; first dequeue: {self.deque[0]}")

        """
        elif self.deque:
            # Otherwise grab from disk (**very slow**)
            # only if there actually have been values
            import warnings
            warnings.warn(
                f"TimeSeriesData averaging from disk data: "
                f"{from_time}->{to_time}"
            )
            for DRecord in self.select_range(from_time, to_time):
                for property in DRecord:
                    if property == 'timestamp':
                        continue
                    DVals[property] += DRecord[property]
                num_vals += 1
        """

        return {
            key: val / num_vals
            for key, val
            in DVals.items()
        }

    #=========================================================================#
    #                  Short-term In-Memory Data Processing                   #
    #=========================================================================#

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
        for DRecord in self.deque:
            val += DRecord[property]
        return val / num_vals
