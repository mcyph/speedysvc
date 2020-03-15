import time
import socket
from _thread import start_new_thread

from speedysvc.client_server.shared_memory.SHMClient import SHMClient
from speedysvc.client_server.base_classes.ServerProviderBase import ServerProviderBase
from speedysvc.client_server.network.consts import len_packer, response_packer
from speedysvc.compression.NullCompression import NullCompression
from speedysvc.serialisation.MarshalSerialisation import MarshalSerialisation
from speedysvc.serialisation.PickleSerialisation import PickleSerialisation
from speedysvc.compression import compression_types


class NetworkServer(ServerProviderBase):
    def __init__(self,
                 server_methods,
                 tcp_bind_address='127.0.0.1',
                 force_insecure_serialisation=False):
        """
        Create a network TCP/IP server which can be used in
        combination with a ServerMethods subclass, and one
        of MultiProcessManager/InProcessManager
        """
        if not force_insecure_serialisation:
            self.__check_security()

        sock = self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((tcp_bind_address, server_methods.port))
        sock.listen(0)

        ServerProviderBase.__init__(self, server_methods)
        start_new_thread(self.__listen_for_conns_loop, ())

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

    def __listen_for_conns_loop(self):
        server = self.sock
        print("Multithreaded server: waiting for connections...")

        while True:
            server.listen(4)
            conn, (ip, port) = server.accept()
            shm_client = SHMClient(self.server_methods)
            start_new_thread(self.run, (conn, shm_client,))

    def run(self, conn, shm_client):
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

        # Client tells the server whether to use
        # compression, as currently implemented
        compression_inst = compression_types.get_by_type_code(recv(1))

        while True:
            actually_compressed, data_len, cmd_len = \
                len_packer.unpack(recv(len_packer.size))
            cmd = recv(cmd_len)
            args = recv(data_len)
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

            #print("SEND:", send_data)
            conn.send(send_data)


if __name__ == '__main__':
    inst = NetworkServer({
        'echo': lambda data: data
    }, port=5555)

    while 1:
        time.sleep(1)
