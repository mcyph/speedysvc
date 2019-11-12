import json
import msgpack
from network_tools.RPCServerBase import RPCServerBase
from network_tools.posix_shm_sockets.SHMSocket import SHMSocket, int_struct


def json_method(fn):
    fn.is_json_method = True


class SHMServer(RPCServerBase):
    def __init__(self, DCmds, port):
        self.port = port
        self.DCmds = DCmds

        self.to_server_socket = SHMSocket(
            socket_name='to_server_%s' % port,
            clean_up=True
        )
        self.DToClientSockets = {}
        self.__main()

    def __main(self):
        while True:
            data = self.to_server_socket.get()
            if not data:
                continue # FIXME!
            print(data)

            client_id = int_struct.unpack(
                data[0:int_struct.size]
            )[0]
            if not client_id in self.DToClientSockets:
                self.DToClientSockets[client_id] = SHMSocket(
                    socket_name='from_server_%s' % self.port,
                    clean_up=False
                )
            to_client_socket = self.DToClientSockets[client_id]

            cmd, _, params = data[int_struct.size:].partition(' ')
            cmd = cmd.decode('ascii')
            fn = self.DCmds[cmd]

            if hasattr(fn, 'is_json_method'):
                to_client_socket.send(self.DCmds[cmd](
                    *json.loads(params.decode('utf-8'))
                ))
            else:
                to_client_socket.send(
                    self.DCmds[cmd](params)
                )

if __name__ == '__main__':
    import time
    inst = SHMServer({
        'echo': lambda data: data
    }, port=5555)

    while 1:
        time.sleep(1)
