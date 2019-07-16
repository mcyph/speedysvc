import time
import socket
import _thread
from json import loads, dumps


class NetworkServer:
    def __init__(self, DCmds, port, host='127.0.0.1'):
        self.DCmds = DCmds

        print("[+] New server socket thread started for "+host+":"+str(port))

        self.server = server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        self.__listen_for_conns_loop()

    def __listen_for_conns_loop(self):
        server = self.server
        while True:
            server.listen(4)
            print("Multithreaded Python server : Waiting for connections from TCP clients...")
            (conn, (ip, port)) = server.accept()
            _thread.start_new(self.run, (conn,))

    def run(self, conn):
        conn.setblocking(True)
        conn.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        while True:
            # Get the command name
            cmd = b''
            while 1:
                cmd += (conn.recv(1) or b'')
                #print(cmd)
                if cmd and cmd[-1] == ord(b' '):
                    break
            cmd = cmd[:-1].decode('ascii')

            # Get the amount of data to receive
            data_amount = b''
            while 1:
                data_amount += (conn.recv(1) or b'')
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
            data = b''.join(LData)

            try:
                fn = self.DCmds[cmd]

                if hasattr(fn, 'is_json'):
                    # Use JSON if method defined using @json_method
                    send_data = dumps(fn(
                        **loads(data.decode('utf-8'))
                    )).encode('utf-8')
                    send_data = str(len(send_data)).encode('ascii') + b'+' + send_data
                else:
                    # Otherwise use raw data
                    send_data = fn(data)
                    send_data = str(len(send_data)).encode('ascii') + b'+' + send_data

            except Exception as exc:
                # Just send a basic Exception instance for now, but would be nice
                # if could recreate some kinds of exceptions on the other end
                import traceback
                traceback.print_exc()
                send_data = repr(exc).encode('utf-8')
                send_data = str(len(send_data)).encode('ascii') + b'-' + send_data

            conn.send(send_data)


if __name__ == '__main__':
    inst = NetworkServer({
        'echo': lambda data: data
    }, port=5555)

    while 1:
        time.sleep(1)
