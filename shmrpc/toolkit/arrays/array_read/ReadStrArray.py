from _thread import allocate_lock


class ReadStrArray:
    typecode = 'u' # HACK!

    def __init__(self, mmap, offset, amount):
        self.offset = int(offset)
        self.amount = int(amount)
        #print 'offset:', offset, amount
        self.mmap = mmap
        self.lock = allocate_lock()

    def __len__(self):
        return self.amount

    def __getitem__(self, item):
        # I use `unicode(str, 'utf-8')` as it's faster than `str.decode('utf-8'),
        # though it will need to be removed if moving to python 3
        offset = self.offset
        amount = self.amount

        def check_idx(x):
            assert x >= 0
            #print x, amount

            if x > amount:
                raise IndexError(x)

        if isinstance(item, slice):
            start = item.start
            stop = item.stop

            assert item.step is None
            check_idx(start)
            check_idx(stop)

            return str(
                self.__read(offset+start, stop-start),
                'utf-8'
            )
        else:
            # Get a single character
            # can only look forwards, so is only useful to
            # ask if something starts with something else(!)
            raise NotImplementedError
            s = ''
            x = item
            check_idx(item)

            while 1:
                s += self.mmap[x+offset]
                if not x & 128:
                    # utf-8 break!
                    break
                x += 1

            return str(s, 'utf-8')

    def get_ascii_char(self, item):
        assert item <= self.amount
        assert item >= 0

        return chr(self.__read(item+self.offset, 1)[0])

    def __read(self, seek, amount):
        if False:
            return self.mmap[seek:seek+amount]
        else:
            with self.lock:
                self.mmap.seek(seek)
                return self.mmap.read(amount)
