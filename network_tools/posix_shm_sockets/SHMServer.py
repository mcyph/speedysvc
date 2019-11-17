import time
import _thread
import traceback
#from toolkit.benchmarking.benchmark import benchmark
from network_tools.RPCServerBase import RPCServerBase
from network_tools.posix_shm_sockets.SHMSocket import SHMSocket, int_struct
from network_tools.MsgPack import MsgPack


def json_method(fn):
    fn.is_json_method = True
    return fn


class SHMServer(RPCServerBase):
    def __init__(self, DCmds, port, init_resources=True, client_timeout=10):
        print('Starting new SHMServer on port:', port)
        self.port = port
        self.client_timeout = client_timeout

        # Make it so that keys are indexed by byte values to
        # prevent having to decode the command each time
        new_DCmds = {}
        for k, v in DCmds.items():
            new_DCmds[k.encode('ascii')] = v
        self.DCmds = new_DCmds
        print("COMMANDS:", self.DCmds)

        self.to_server_socket = SHMSocket(
            socket_name='to_server_%s' % port,
            init_resources=init_resources
        )

        self.DToClientSockets = {}
        _thread.start_new_thread(
            self.__reap_client_sockets, ()
        )
        _thread.start_new_thread(self.__main, ())

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
                elif client_socket.get_sockets_destroyed():
                    L.append(client_id)

            for client_id in L:
                print("Reaping socket to client: %s" % client_id)
                del self.DToClientSockets[client_id]

            time.sleep(self.client_timeout/2)

    #@benchmark(restrictions=(30,))
    def __main(self):
        """
        Process RPC calls forever.
        """

        # t_from = time.time()
        # while time.time()-t_from < 20:

        while True:
            # TODO: Should there be better error handling here?
            # The trouble is, nothing should ever be allowed to
            # go wrong here - if it does, perhaps the server
            # should die anyway(?)
            data = self.to_server_socket.get(timeout=None)
            client_id = int_struct.unpack(data[0:int_struct.size])[0]
            to_client_socket = self.__get_client_socket(client_id)
            cmd, params = data[int_struct.size:].split(b' ', 1)

            if cmd == b'heartbeat':
                try:
                    to_client_socket.put(b'+'+params, timeout=10)
                except:
                    traceback.print_exc()
            else:
                try:
                    fn = self.DCmds[cmd]
                    if hasattr(fn, 'is_json_method'):
                        send_data = b'+'+MsgPack.dumps(
                            fn(*MsgPack.loads(params))
                        )
                    else:
                        send_data = b'+'+fn(params)

                except Exception as exc:
                    # Just send a basic Exception instance for now, but would be nice
                    # if could recreate some kinds of exceptions on the other end
                    send_data = b'-' + repr(exc).encode('utf-8')
                    traceback.print_exc()

                try:
                    to_client_socket.put(send_data, timeout=10)
                except:
                    traceback.print_exc()

    def __get_client_socket(self, client_id):
        """
        Get a SHMSocket object that allows sending
        the return values of RPC calls to clients
        :param client_id: the integer ID of the client
        :return: a SHMSocket object
        """
        if client_id in self.DToClientSockets:
            # Can only send to client if the socket hasn't
            # been destroyed on the client end!
            client_socket = self.DToClientSockets[client_id]
            if client_socket.get_sockets_destroyed():
                del self.DToClientSockets[client_id]

        if not client_id in self.DToClientSockets:
            # Create the connection to the client
            socket_name = 'from_server_%s_%s' % (self.port, client_id)
            self.DToClientSockets[client_id] = SHMSocket(
                socket_name=socket_name,
                init_resources=False
            )
            print(f"__get_client_socket: {socket_name}")

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
