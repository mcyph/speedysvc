import time
import socket
from toolkit.documentation.copydoc import copydoc

from network_tools.rpc.base_classes.ClientProviderBase import \
    ClientProviderBase


class NetworkClient(ClientProviderBase):
    def __init__(self, server_methods, host='127.0.0.1'):
        """

        :param server_methods:
        :param host:
        """
        self.conn_to_server = conn_to_server = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        conn_to_server.setsockopt(
            socket.SOL_TCP, socket.TCP_NODELAY, 1
        )
        conn_to_server.connect((host, server_methods.port))
        ClientProviderBase.__init__(self, server_methods)

    def __del__(self):
        self.conn_to_server.close()

    @copydoc(ClientProviderBase.send)
    def send(self, fn, data):
        data = fn.serialiser.dumps(data)

        self.conn_to_server.send(
            fn.__name__.encode('ascii') + b' ' +
            str(len(data)).encode('ascii') + b' '
        )
        self.conn_to_server.send(data)

        # Get number of bytes
        data_amount = b''
        while 1:
            append = self.conn_to_server.recv(1)
            if append in b'+-':
                status = append
                break
            elif append:
                data_amount += append
        data_amount = int(data_amount)

        # Get the server's response
        LData = []
        while data_amount > 0:
            get_amount = (
                1024 if data_amount > 1024
                else data_amount
            )
            append = self.conn_to_server.recv(get_amount)
            if append:
                LData.append(append)
                data_amount -= len(append)

        #print(data_amount, LData)

        if status == b'+':
            return fn.serialiser.loads(b''.join(LData))
        else:
            raise Exception(b''.join(LData).decode('utf-8'))


if __name__ == '__main__':
    inst = NetworkClient(5555)
    t = time.time()
    for x in range(500000):
        i = b"my vfdsfdsfsdfsdfsdfdsfsdaluetasdsadasdsadsadsaest"# bytes([randint(0, 255)])*500
        #print('SEND:', i)
        assert inst.send('echo', i) == i

    print(time.time()-t)
