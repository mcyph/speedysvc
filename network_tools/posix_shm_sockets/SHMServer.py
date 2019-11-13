import json
import _thread
import msgpack
from network_tools.RPCServerBase import RPCServerBase
from network_tools.posix_shm_sockets.SHMSocket import SHMSocket, int_struct


def json_method(fn):
    fn.is_json_method = True


class SHMServer(RPCServerBase):
    def __init__(self, DCmds, port,
                 init_resources=True,
                 client_timeout=10):

        self.port = port
        self.client_timeout = client_timeout

        # Make it so that keys are indexed by byte values to
        # prevent having to decode the command each time
        new_DCmds = {}
        for k, v in DCmds.items():
            new_DCmds[k.encode('ascii')] = v
        self.DCmds = new_DCmds

        self.to_server_socket = SHMSocket(
            socket_name='to_server_%s' % port,
            init_resources=init_resources
        )

        self.DToClientSockets = {}
        _thread.start_new_thread(
            self.__reap_client_sockets, ()
        )

        self.__main()

    def __reap_client_sockets(self):
        """
        Periodically clean out client sockets
        which haven't been used in some time
        """
        while 1:
            L = []
            for client_id, client_socket in list(self.DToClientSockets.items()):
                if time.time()-client_socket.get_last_used_time() > self.client_timeout:
                    L.append(client_id)

            for client_id in L:
                del self.DToClientSockets[client_id]

            time.sleep(self.client_timeout/2)

    def __main(self):
        """
        Process RPC calls forever.
        """
        while True:
            data = self.to_server_socket.get()
            client_id = int_struct.unpack(data[0:int_struct.size])[0]
            to_client_socket = self.__get_client_socket(client_id)

            cmd, params = data[int_struct.size:].split(b' ', 1)
            fn = self.DCmds[cmd]

            if hasattr(fn, 'is_json_method'):
                to_client_socket.put(self.DCmds[cmd](
                    *json.loads(params.decode('utf-8'))
                ))
            else:
                to_client_socket.put(
                    self.DCmds[cmd](params)
                )

    def __get_client_socket(self, client_id):
        """
        Get a SHMSocket object that allows sending
        the return values of RPC calls to clients
        :param client_id: the integer ID of the client
        :return: a SHMSocket object
        """
        if not client_id in self.DToClientSockets:
            self.DToClientSockets[client_id] = SHMSocket(
                socket_name='from_server_%s_%s' % (self.port, client_id),
                init_resources=False
            )
        return self.DToClientSockets[client_id]


if __name__ == '__main__':
    import time

    def run(init_resources=True):
        inst = SHMServer({
            'echo': lambda data: data
        },
        port=5555,
        init_resources=init_resources)

        while 1:
            time.sleep(1)

    if False:
        run()
    else:
        import multiprocessing
        LProcesses = []

        for x in range(12):
            process = multiprocessing.Process(
                target=run,
                kwargs={'init_resources': not x}
            )
            LProcesses.append(process)
            process.start()

            if not x:
                time.sleep(1)

        while 1:
            time.sleep(1)
