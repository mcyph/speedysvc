from shmrpc.ipc.JSONMMapBase import JSONMMapBase


class JSONMMapList(JSONMMapBase):
    def __init__(self, port, create):
        JSONMMapBase.__init__(self, port, create)

        # Set an initial blank list
        # if creating for first time
        if create:
            with self:
                self._encode([])

                print(self._decode())

    def __enter__(self):
        # Allow for `with JSONMapArray(..)` syntax
        self.lock.lock()
        self.lock_acquired = True

    def __exit__(self, type, value, traceback):
        self.lock_acquired = False
        self.lock.unlock()

    def __len__(self):
        assert self.lock_acquired
        r = len(self._decode())
        return r

    def __getitem__(self, item):
        assert self.lock_acquired
        L = self._decode()
        r = L[item]
        return r

    def __delitem__(self, item):
        assert self.lock_acquired
        L = self._decode()
        del L[item]
        self._encode(L)

    def __iter__(self):
        assert self.lock_acquired
        L = self._decode()
        for i in L:
            yield i

    def append(self, item):
        assert self.lock_acquired
        L = self._decode()
        L.append(item)
        self._encode(L)

    def insert(self, position, item):
        assert self.lock_acquired
        L = self._decode()
        L.insert(position, item)
        self._encode(L)
