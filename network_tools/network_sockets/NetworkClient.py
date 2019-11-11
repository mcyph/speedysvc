import time
import socket
import msgpack
from json import dumps, loads


class NetworkClient:
    def __init__(self, port, host='127.0.0.1'):
        self.conn_to_server = conn_to_server = \
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_to_server.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        conn_to_server.connect((host, port))

    def __del__(self):
        self.conn_to_server.close()

    def send(self, cmd, data):
        self.conn_to_server.send(
            cmd.encode('ascii') + b' ' +
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
            return b''.join(LData)
        else:
            raise Exception(b''.join(LData).decode('utf-8'))

    def send_json(self, cmd, data):
        """
        The same as send(), but sends and receives as JSON
        """
        data = dumps(data).encode('utf-8')
        return loads(self.send(cmd, data), encoding='utf-8')

    def send_msgpack(self, cmd, data):
        """
        The same as send(), but sends and receives as msgpack,
        although I doubt performance will be the primary consideration for NetworkClient.
        note lists will be output as tuples here for performance.
        """
        data = msgpack.dumps(data)
        return msgpack.loads(
            self.send(cmd, data),
            encoding='utf-8',
            use_bin_type=True
        )


if __name__ == '__main__':
    from random import randint

    inst = NetworkClient(5555)
    t = time.time()
    for x in range(100000):
        i = bytes([randint(0, 255)])*500
        #print('SEND:', i)
        assert inst.send('echo', i) == i

    print(time.time()-t)
