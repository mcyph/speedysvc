from io import BytesIO


class MemoryCachedLog:
    def __init__(self, path, max_cache=500000):  # 500kb
        """
        A disk-backed log, with a FIFO in-memory buffer that
        :param path:
        :param max_cache:
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
        (kind-of like a seek position that wraps around)
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
            data = (
                self.cache[self.spindle:] + self.cache[:self.spindle]
            )
        elif offset > self.spindle:
            # Spindle has moved back past 0 (potentially multiple times,
            # causing bugs - though I don't think this edge case matters
            # enough to fix it doing so would need more
            # complex logic/reduce performance).
            # Wrap around!
            data = (
                self.cache[offset:] + self.cache[:self.spindle]
            )
        elif offset < self.spindle:
            # Just return the amount up to the spindle
            data = self.cache[offset:self.spindle]
        else:
            # Nothing to return
            return

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

        if self.spindle+len(s) > self.max_cache:
            self.cache.seek(0)
            self.cache.write(s[up_to_bytes:])
            self.spindle = len(s)-up_to_bytes


if __name__ == '__main__':
    mcl = MemoryCachedLog(path='/tmp/mcl_test', max_cache=200)

    for x in range(2000):
        mcl._write_line(str(x).encode('ascii'))

    for x in mcl._iter_from_cache():
        print(x)

    for x in mcl._iter_from_disk():
        print(x)

