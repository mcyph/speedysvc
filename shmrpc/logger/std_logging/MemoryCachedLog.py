from io import BytesIO


class MemoryCachedLog:
    def __init__(self, path, max_cache=500000):  # 500kb
        """
        A disk-backed log, with a circular FIFO in-memory buffer that
        overwrites itself after max_cache is reached.

        Note that subclasses should provide locking as needed,
        as the functions in this class are not threadsafe.

        :param path: the path on disk to write log entries to
        :param max_cache: the maximum amount of bytes to store as
                          cache in a BytesIO
        """
        self.spindle = 0
        self.cache = BytesIO()
        self.max_cache = max_cache
        self.f = open(path, 'wb+')

    def __del__(self):
        """
        Make sure caches are flushed.
        """
        self.f.close()

    def get_fifo_spindle(self):
        """
        Get the current relative position of the FIFO in-memory buffer
        (kind-of like a seek position that wraps around in the cache)

        This is the value to pass as offset to _iter_from_cache if you
        want to continue on from where you were last time, without
        having to re-read the whole thing

        :return: an int
        """
        return self.spindle

    def _iter_from_disk(self):
        """
        Iterate through log items on disk, delimited by newlines.
        """
        self.f.seek(0, 0)  # relative to start
        for line in self.f:
            yield line
        self.f.seek(0, 2)  # relative to end

    def _iter_from_cache(self, offset=None):
        """
        Iterate through only whole items from the in-memory FIFO
        cache, optionally from the "offset", which is the previous
        spindle value. This can be useful if you only want log
        items from last poll.
        """
        if offset is None:
            # Get the whole amount of data
            self.cache.seek(self.spindle)
            data = self.cache.read(self.max_cache-self.spindle)
            self.cache.seek(0)
            data += self.cache.read(self.spindle)

        elif offset > self.spindle:
            # Spindle has moved back past 0 (potentially multiple times,
            # causing bugs - though I don't think this edge case matters
            # enough to fix it as doing so would need more
            # complex logic/reduce performance).
            # Wrap around!
            self.cache.seek(offset)
            data = self.cache.read(self.max_cache-offset)
            self.cache.seek(0)
            data += self.cache.read(self.spindle)

        elif offset < self.spindle:
            # Just return the amount up to the spindle
            self.cache.seek(offset)
            data = self.cache.read(self.spindle-offset)

        else:
            # Nothing to return
            return

        self.cache.seek(self.spindle)
        for x, line in enumerate(data.split(b'\n')):
            if not x:
                continue
            yield line

    def _write_line(self, s):
        """
        Write a line both to the in-memory FIFO buffer and file on disk
        :param s: the line to write. This cannot contain any newlines
        """
        assert not b'\n' in s, \
            "Each log entry shouldn't contain newlines!"
        self.f.write(s+b'\n')
        s = b'\n'+s

        up_to_bytes = self.max_cache-self.spindle
        self.cache.write(s[:up_to_bytes])
        #print(self.cache.tell())

        if (self.spindle+len(s)) > self.max_cache:
            #print("SEEKING TO 0!")
            self.cache.seek(0)
            self.cache.write(s[up_to_bytes:])
            self.spindle = len(s)-up_to_bytes
        else:
            self.spindle += len(s)


if __name__ == '__main__':
    mcl = MemoryCachedLog(path='/tmp/mcl_test', max_cache=200)

    for x in range(200):
        mcl._write_line(str(x).encode('ascii'))

    for x in mcl._iter_from_cache():
        print(x)

    for x in mcl._iter_from_disk():
        print(x)

    for x in mcl._iter_from_cache(50):
        print(x)

    # mcl.cache.seek(0)
    # print(mcl.cache.read())
