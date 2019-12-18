import time
import _thread
import signal
import traceback
from random import getrandbits
#from toolkit.benchmarking.benchmark import benchmark
from network_tools.rpc.base_classes.ServerProviderBase import \
    ServerProviderBase
from network_tools.rpc.shared_memory.shm_socket.ResponseSHMSocket import \
    ResponseSHMSocket
from network_tools.rpc.shared_memory.shm_socket.RequestSHMSocket import \
    RequestSHMSocket


def json_method(fn):
    fn.is_json_method = True
    return fn


class SHMServer(ServerProviderBase):
    def __init__(self, client_timeout=10):
        """
        :param init_resources:
        :param client_timeout:
        """
        self.client_timeout = client_timeout

    def __call__(self, server_methods, init_resources=True):
        print(f"{server_methods.name}:{server_methods.port}: "
              f"SHMServer __call__; init_resources:", init_resources)
        # NOTE: init_resources should only be called if creating from scratch -
        # if connecting to an existing socket, init_resources should be False!
        ServerProviderBase.__call__(self, server_methods)

        print('Starting new SHMServer on port:',
              server_methods.port, init_resources)
        port = self.port = server_methods.port

        self.request_socket = RequestSHMSocket(
            socket_name='to_server_%s' % port,
            init_resources=init_resources
        )

        self.shut_me_down = False

        self.DResponseSHMSockets = {}
        _thread.start_new_thread(self.__reap_client_sockets, ())
        _thread.start_new_thread(self.__main, ())
        signal.signal(signal.SIGINT, self.__on_sigint)

    def __on_sigint(self, *args):
        self.shut_me_down = True

    def __reap_client_sockets(self):
        """
        Periodically clean out client sockets
        which haven't been used in some time
        """
        while 1:
            L = []
            for client_id, client_socket in list(self.DResponseSHMSockets.items()):
                if time.time()-client_socket.get_last_used_time() > self.client_timeout:
                    L.append(client_id)
                elif client_socket.get_sockets_destroyed():
                    L.append(client_id)

            for client_id in L:
                #print("Reaping socket to client: %s" % client_id)
                del self.DResponseSHMSockets[client_id]

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
            #print(f"{self.server_methods.name}: "
            #      f"Getting from {self.request_socket.socket_name}")
            echo_me, cmd, args, client_id = self.request_socket.get(timeout=-1)
            response_socket = self.__get_response_socket(client_id)
            #print(f"{self.server_methods.name}:{self.server_methods.port} "
            #      f"Handling command:", cmd, args)

            if cmd == b'heartbeat':
                try:
                    response_socket.put(echo_me, b'+'+args, timeout=-1)
                except:
                    traceback.print_exc()
            else:
                try:
                    result = self.handle_fn(cmd, args)
                    send_data = b'+' + result

                except Exception as exc:
                    # Just send a basic Exception instance for now, but would be nice
                    # if could recreate some kinds of exceptions on the other end
                    send_data = b'-' + repr(exc).encode('utf-8')
                    traceback.print_exc()

                #print(f"{self.server_methods.name}:"
                #      f"{self.server_methods.port}: "
                #      f"putting {send_data[:20]}")

                try:
                    response_socket.put(echo_me, send_data, timeout=3)
                except:
                    traceback.print_exc()

            if self.shut_me_down:
                raise SystemExit("Shutdown requested via SIGINT")

    def __get_response_socket(self, client_id):
        """
        Get a SHMSocket object that allows sending
        the return values of RPC calls to clients
        :param client_id: the integer ID of the client
        :return: a SHMSocket object
        """
        if client_id in self.DResponseSHMSockets:
            # Can only send to client if the socket hasn't
            # been destroyed on the client end!
            client_socket = self.DResponseSHMSockets[client_id]
            if client_socket.get_sockets_destroyed():
                del self.DResponseSHMSockets[client_id]

        if not client_id in self.DResponseSHMSockets:
            # Create the connection to the client
            socket_name = 'from_server_%s_%s' % (self.port, client_id)
            self.DResponseSHMSockets[client_id] = ResponseSHMSocket(
                socket_name=socket_name,
                init_resources=False
            )
            #print(f"__get_response_socket: {socket_name}")

        return self.DResponseSHMSockets[client_id]


if __name__ == '__main__':
    import time

    def run(init_resources=True):
        inst = SHMServer({
            'echo': lambda data: data
        })
        inst(
            port=5555,
            init_resources=init_resources
        )

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
