import json
from struct import Struct
from hybrid_lock import HybridSpinSemaphore, CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE
from network_tools.rpc.shared_memory.shared_params import get_mmap


class JSONMMapArray:
    def __init__(self, port, create):
        self.lock = HybridSpinSemaphore(
            f'sem_{port}_pids'.encode('ascii'),
            CREATE_NEW_OVERWRITE
            if create
            else CONNECT_TO_EXISTING,
            initial_value=1
        )

        # I think 32kb is a good size - pretty unlikely to
        # exceed this size, and also in the scheme of things
        # isn't that much memory IMO.
        self.mmap = get_mmap(
            f'mmap_{port}_pids'.encode('ascii'),
            create, new_size=32767
        )

        self.len_struct = Struct(f'!I')
        self.lock_acquired = False

        # Set an initial blank list
        # if creating for first time
        if create:
            with self:
                self.__encode([])

                print(self.__decode())

    def __enter__(self):
        # Allow for `with JSONMapArray(..)` syntax
        self.lock.lock()
        self.lock_acquired = True

    def __exit__(self, type, value, traceback):
        self.lock_acquired = False
        self.lock.unlock()

    def __len__(self):
        assert self.lock_acquired
        r = len(self.__decode())
        return r

    def __getitem__(self, item):
        assert self.lock_acquired
        L = self.__decode()
        r = L[item]
        return r

    def __delitem__(self, item):
        assert self.lock_acquired
        L = self.__decode()
        del L[item]
        self.__encode(L)

    def __iter__(self):
        assert self.lock_acquired
        L = self.__decode()
        for i in L:
            yield i

    def append(self, item):
        assert self.lock_acquired
        L = self.__decode()
        L.append(item)
        self.__encode(L)

    def insert(self, position, item):
        assert self.lock_acquired
        L = self.__decode()
        L.insert(position, item)
        self.__encode(L)

    def __decode(self):
        assert self.lock_acquired
        amount = self.len_struct.unpack(
            self.mmap[0:self.len_struct.size]
        )[0]
        data = self.mmap[
            self.len_struct.size:
            self.len_struct.size+amount
        ].decode('utf-8')
        #print("DECODING:", data, self.len_struct.size, self.len_struct.size+len(data))
        return json.loads(data)

    def __encode(self, L):
        assert self.lock_acquired
        encoded = json.dumps(L).encode('utf-8')
        self.mmap[0:self.len_struct.size] = \
            self.len_struct.pack(len(encoded))
        from_ = self.len_struct.size
        to = from_ + len(encoded)
        #print("ENCODED:", encoded, from_, to, type(from_), type(to))
        #print("REPLACING:", self.mmap[from_:to], "WITH:", encoded, len(self.mmap))
        self.mmap[from_:to] = encoded
