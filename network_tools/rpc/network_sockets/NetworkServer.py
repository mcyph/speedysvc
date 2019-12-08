import time
import socket
import snappy
import _thread

from network_tools.rpc.base_classes.ServerProviderBase import \
    ServerProviderBase
from network_tools.rpc.network_sockets.consts import \
    len_packer, response_packer


class NetworkServer(ServerProviderBase):
    def __init__(self, server_methods, host='127.0.0.1'):
        """

        :param server_methods:
        :param host:
        """
        ServerProviderBase.__init__(self, server_methods)

        self.server = server = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, server_methods.port))
        self.__listen_for_conns_loop()

    def __listen_for_conns_loop(self):
        server = self.server
        while True:
            server.listen(4)
            print("Multithreaded server: waiting for connections...")
            (conn, (ip, port)) = server.accept()
            _thread.start_new(self.run, (conn,))

    def run(self, conn):
        conn.setblocking(True)
        conn.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        def recv(amount):
            # Note string concatenation is slower in earlier versions
            # of python, but should be faster than list concat in later
            # versions after 3.
            r = b''
            while len(r) != amount:
                r += conn.recv(amount)
            return r

        while True:
            data_len, cmd_len = len_packer.unpack(
                recv(len_packer.size)
            )
            cmd = recv(cmd_len)
            args = snappy.uncompress(
                recv(data_len)
            )
            #print(data_len, cmd_len, cmd, args)

            try:
                send_data = snappy.compress(
                    self.handle_fn(cmd, args)
                )
                send_data = (
                    response_packer.pack(len(send_data), b'+') +
                    send_data
                )

            except Exception as exc:
                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                import traceback
                traceback.print_exc()
                send_data = repr(exc).encode('utf-8')
                send_data = (
                    response_packer.pack(len(send_data), b'-') +
                    send_data
                )

            #print("SEND:", send_data)
            conn.send(send_data)


if __name__ == '__main__':
    inst = NetworkServer({
        'echo': lambda data: data
    }, port=5555)

    while 1:
        time.sleep(1)
