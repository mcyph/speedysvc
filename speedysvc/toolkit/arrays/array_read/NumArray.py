from _thread import allocate_lock
from struct import unpack, calcsize
# A basic numpy dropin for PyPy


DTypes = {
    'uint8': '<B',
    'uint16': '<H',
    'uint32': '<I',
    'uint64': '<Q',

    'int8': '<b',
    'int16': '<h',
    'int32': '<i',
    'int64': '<q'
}


def check_sizes():
    for k, v in list(DTypes.items()):
        assert calcsize(v) == int(k.split('int')[-1]) // 8


check_sizes()

DEBUG = False


class NumArray:
    # dtype=typecode, buffer=mm, offset=seek, shape=(amount,)
    def __init__(self, dtype, buffer, offset, shape):
        assert len(shape) == 1
        self.amount = int(shape[0])
        self.buffer = buffer
        self.offset = int(offset)
        self.lock = allocate_lock()

        tc = self.typecode = DTypes[dtype]
        self.size = calcsize(tc)

        #for i in xrange(len(self)):
        #    print i, self[i], len(self)

        # TODO: It would be better to have this lock per mmap buffer, rather than global!! ======================================

        if DEBUG:
            import numpy as np
            self.nd_ref = np.ndarray(dtype=dtype, buffer=buffer, offset=offset, shape=shape)

    def __len__(self):
        return self.amount

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __getitem__(self, item):
        #with self.lock:
        assert isinstance(item, int)

        start = self.offset+(self.size*item)
        array_end = self.offset+(self.size*self.amount)-self.size
        if start > array_end:
            raise IndexError(
                "index %s array position %s array end %s size %s amount %s offset %s" % (
                    item, start, array_end, self.size, self.amount, self.offset
                )
            )

        with self.lock:
            self.buffer.seek(start)
            data = self.buffer.read(self.size)

        #data = self.buffer[start:start+self.size]
        r = unpack(self.typecode, data)[0]

        #print item, self.amount, self.offset, start, r
        if DEBUG:
            def run_me():
                if r != self.nd_ref[item]:
                    print("NUMARRAY VALUE ERROR!!!!!!!")
                    raise ValueError((self.nd_ref[item], r, self.typecode))

            from _thread import start_new_thread
            start_new_thread(run_me, ())
        return r

if __name__ == '__main__':
    import numpy as np

    for typ in DTypes:
        print((typ, DTypes[typ], calcsize(DTypes[typ]), np.dtype(typ).itemsize))

        npar = np.ndarray(typ, buffer(struct.pack()))
