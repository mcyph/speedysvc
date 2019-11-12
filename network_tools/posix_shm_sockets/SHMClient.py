import json
import struct
import msgpack
from network_tools.RPCClientBase import RPCClientBase
from network_tools.posix_shm_sockets.SHMSocket import SHMSocket, int_struct


class SHMClient(RPCClientBase):
    def __init__(self, port):
        RPCClientBase.__init__(self, port)

        self.to_server_socket = SHMSocket(
            socket_name='to_server_%s' % port,
            clean_up=False
        )
        self.from_server_socket = SHMSocket(
            socket_name='from_server_%s' % port,
            clean_up=True
        )
        self.client_id = self._acquire_lock()
        self.client_id_as_bytes = int_struct.pack(
            self.client_id
        )

    def send(self, cmd, data):
        print(self.client_id_as_bytes, data)
        self.to_server_socket.put(
            self.client_id_as_bytes+
            cmd.encode('ascii')+b' '+data
        )

    def send_json(self, cmd, data):
        self.to_server_socket.put(
            self.client_id_as_bytes+
            cmd.encode('ascii')+b' '+
            json.dumps(data).encode('utf-8')
        )

    def send_msgpack(self, cmd, data):
        self.to_server_socket.put(
            self.client_id_as_bytes+
            cmd.encode('ascii')+b' '+
            msgpack.dumps(data)
        )

if __name__ == '__main__':
    import time
    from random import randint

    LInsts = []
    for x in range(10):
        inst = SHMClient(5555)
        LInsts.append(inst)

    t = time.time()

    for x in range(100000):
        i = b'blah'#bytes([randint(0, 255)])*500
        #print('SEND:', i)
        #for inst in LInsts:
        data = LInsts[0].send('echo', i)
        assert data == i, (data, i)

    print(time.time()-t)
