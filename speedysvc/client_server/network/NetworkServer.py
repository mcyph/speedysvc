import time
import socket
from _thread import start_new_thread

from speedysvc.compression import compression_types
from speedysvc.compression.NullCompression import NullCompression
from speedysvc.client_server.shared_memory.SHMClient import SHMClient
from speedysvc.serialisation.PickleSerialisation import PickleSerialisation
from speedysvc.serialisation.MarshalSerialisation import MarshalSerialisation
from speedysvc.client_server.network.consts import len_packer, response_packer
from speedysvc.client_server.base_classes.ServerProviderBase import ServerProviderBase


class NetworkServer(ServerProviderBase):
    def __init__(self,
                 server_methods,
                 port: int,
                 service_name: str,
                 bind_interface: str = '127.0.0.1',
                 force_insecure_serialisation: bool = False):
        """
        Create a network TCP/IP server which can be used in
        combination with a ServerMethods subclass, and one
        of MultiProcessManager/InProcessManager
        """
        if not force_insecure_serialisation:
            self.__check_security()

        sock = self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.bind((bind_interface, port))
        sock.listen(0)

        ServerProviderBase.__init__(self,
                                    server_methods=server_methods,
                                    port=port,
                                    service_name=service_name)

    def __check_security(self):
        for name in dir(self):
            attr = getattr(self, name)
            if hasattr(attr, 'serialiser'):
                _serialiser = attr.serialiser
                if isinstance(_serialiser, (PickleSerialisation, MarshalSerialisation)):
                    raise Exception(
                        "Pickle/marshal serialisation disallowed by default when using "
                        "NetworkServer (TCP server) for security reasons; "
                        "force_insecure_serialisation=True can be set, but only do it "
                        "if you know what you're doing. It may be preferable to use JSON/raw "
                        "depending on your use case."
                    )

    def serve_forever_in_new_thread(self):
        start_new_thread(self.serve_forever, ())

    def serve_forever(self):
        server = self.sock
        #print("Multithreaded server: waiting for connections...")

        while True:
            server.listen(4)
            conn, (ip, port) = server.accept()
            # If we're using tcp sockets, spinlocks can
            # actually be counterproductive and harm performance
            # as we'd be waiting too long too often
            shm_client = SHMClient(self.server_methods, use_spinlock=False)
            start_new_thread(self.run, (conn, shm_client,))

    def run(self, conn, shm_client):
        # TODO: Provide basic support for REST-based RPC
        #       if the client starts with an HTTP header! =============================================================s

        conn.setblocking(True)

        # If this setting isn't set, then there's a high
        # probability of there being much higher latency
        conn.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        def recv(amount):
            # Note string concatenation is slower in earlier versions
            # of python, but should be faster than list concat in later
            # versions after 3.
            r = b''
            while len(r) != amount:
                i = conn.recv(amount)
                if i:
                    r += i
                else:
                    raise ConnectionResetError()
            return r

        # Client tells the server whether to use
        # compression, as currently implemented
        try:
            compression_inst = compression_types.get_by_type_code(recv(1))
        except ConnectionResetError:
            return

        while True:
            try:
                actually_compressed, data_len, cmd_len = \
                    len_packer.unpack(recv(len_packer.size))
                cmd = recv(cmd_len)
                args = recv(data_len)
            except ConnectionResetError:
                return

            if actually_compressed:
                args = compression_inst.decompress(args)

            try:
                send_data = shm_client.send(cmd, args)
                actually_compressed, send_data = \
                    compression_inst.compress(send_data)
                send_data = (
                    response_packer.pack(
                        actually_compressed,
                        len(send_data),
                        b'+'
                    ) + send_data
                )
            except Exception as exc:
                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                import traceback
                traceback.print_exc()
                send_data = repr(exc).encode('utf-8')
                send_data = (
                    # Won't compress exceptions, for now
                    response_packer.pack(
                        False,
                        len(send_data),
                        b'-'
                    ) + send_data
                )

            conn.send(send_data)


if __name__ == '__main__':
    inst = NetworkServer({
        'echo': lambda data: data
    }, port=5555)

    while True:
        time.sleep(1)
