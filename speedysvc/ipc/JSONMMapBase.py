import json
from abc import ABC
from struct import Struct
from hybrid_lock import HybridLock, CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE
from speedysvc.client_server.shared_memory.shared_params import get_mmap


class JSONMMapBase(ABC):
    def __init__(self, port, create):
        self.lock = HybridLock(
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

    def _decode(self):
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

    def _encode(self, L):
        assert self.lock_acquired
        encoded = json.dumps(L).encode('utf-8')
        self.mmap[0:self.len_struct.size] = \
            self.len_struct.pack(len(encoded))
        from_ = self.len_struct.size
        to = from_ + len(encoded)
        #print("ENCODED:", encoded, from_, to, type(from_), type(to))
        #print("REPLACING:", self.mmap[from_:to], "WITH:", encoded, len(self.mmap))
        self.mmap[from_:to] = encoded
