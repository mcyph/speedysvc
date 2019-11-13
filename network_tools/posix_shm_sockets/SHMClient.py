import json
import struct
import msgpack
from toolkit.documentation.copydoc import copydoc
from network_tools.RPCClientBase import RPCClientBase
from network_tools.posix_shm_sockets.SHMSocket import SHMSocket, int_struct


class SHMClient(RPCClientBase):
    def __init__(self, port):
        RPCClientBase.__init__(self, port)

        # Create a connection to the server(s)
        self.to_server_socket = SHMSocket(
            socket_name='to_server_%s' % port,
            init_resources=False
        )

        self.client_id = client_id = self._acquire_lock()
        self.client_id_as_bytes = int_struct.pack(self.client_id)

        self.from_server_socket = SHMSocket(
            socket_name='from_server_%s_%s' % (port, client_id),
            init_resources=True
        )

    @copydoc(RPCClientBase.send)
    def send(self, cmd, data):
        self.to_server_socket.put(
            self.client_id_as_bytes+
            cmd.encode('ascii')+b' '+data
        )
        return self.from_server_socket.get()

    @copydoc(RPCClientBase.send_json)
    def send_json(self, cmd, data):
        return json.loads(self.send(
            cmd, json.dumps(data).encode('utf-8')
        ))

    @copydoc(RPCClientBase.send_msgpack)
    def send_msgpack(self, cmd, data):
        return msgpack.loads(self.send(
            cmd, msgpack.dumps(data).encode('utf-8')
        ))


if __name__ == '__main__':
    import time
    from random import randint

    LInsts = []
    for x in range(2):
        inst = SHMClient(5555)
        LInsts.append(inst)

    t = time.time()

    for x in range(100000):
        for inst in LInsts:
            #print('SEND:', i)
            #for inst in LInsts:
            i = str(randint(0, 9999999999999)).encode('ascii')*50
            data = inst.send('echo', i)
            assert data == i, (data, i)
            #print(data)

    print(time.time()-t)
