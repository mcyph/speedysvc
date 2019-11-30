import time
import socket
import _thread

from network_tools.rpc.abstract_base_classes.ServerProviderBase import \
    ServerProviderBase


class NetworkServer(ServerProviderBase):
    def __init__(self, server_methods, host='127.0.0.1'):
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

        while True:
            # Get the command name
            cmd = b''
            while 1:
                append = conn.recv(1)
                if not append:
                    return  # Connection closed
                cmd += append
                #print(cmd)
                if cmd and cmd[-1] == ord(b' '):
                    break
            cmd = cmd[:-1].decode('ascii')

            # Get the amount of data to receive
            data_amount = b''
            while 1:
                append = conn.recv(1)
                if not append:
                    return
                data_amount += append
                if data_amount and data_amount[-1] == ord(b' '):
                    break
            data_amount = int(data_amount[:-1])

            # Get the data
            LData = []
            while data_amount > 0:
                get_amount = (
                    1024 if data_amount > 1024
                    else data_amount
                )
                append = conn.recv(get_amount)
                if append:
                    LData.append(append)
                    data_amount -= len(append)
            args = b''.join(LData)

            try:
                send_data = self.handle_fn(cmd, args)
                send_data = (
                    str(len(send_data)).encode('ascii') + b'+' +
                    send_data
                )

            except Exception as exc:
                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                import traceback
                traceback.print_exc()
                send_data = repr(exc).encode('utf-8')
                send_data = (
                    str(len(send_data)).encode('ascii') + b'-' +
                    send_data
                )

            conn.send(send_data)


if __name__ == '__main__':
    inst = NetworkServer({
        'echo': lambda data: data
    }, port=5555)

    while 1:
        time.sleep(1)
