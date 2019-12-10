import time
import socket
from _thread import start_new_thread

from network_tools.rpc.base_classes.ServerProviderBase import ServerProviderBase
from network_tools.rpc.network.consts import len_packer, response_packer
from network_tools.compression.NullCompression import NullCompression


class NetworkServer(ServerProviderBase):
    def __init__(self,
                 server_methods,
                 tcp_bind_address='127.0.0.1',
                 compression_inst=None):
        """
        Create a network TCP/IP server which can be used in
        combination with a ServerMethods subclass, and one
        of MultiProcessManager/InProcessManager
        """
        sock = self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((tcp_bind_address, server_methods.port))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.listen(0)

        if compression_inst is None:
            compression_inst = NullCompression()
        self.compression_inst = compression_inst

    def __call__(self, server_methods):
        ServerProviderBase.__call__(self, server_methods)
        start_new_thread(self.__listen_for_conns_loop, ())

    def __listen_for_conns_loop(self):
        server = self.sock
        while True:
            server.listen(4)
            print("Multithreaded server: waiting for connections...")
            conn, (ip, port) = server.accept()
            start_new_thread(self.run, (conn,))

    def run(self, conn):
        # TODO: Provide basic support for REST-based RPC
        #       if the client starts with an HTTP header! =============================================================

        conn.setblocking(True)

        # If this setting isn't set, then there's a high
        # probability of there being much higher latency
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
            args = self.compression_inst.uncompress(
                recv(data_len)
            )
            #print(data_len, cmd_len, cmd, args)

            try:
                send_data = self.compression_inst.compress(
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
