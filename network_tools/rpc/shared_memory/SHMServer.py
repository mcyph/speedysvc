import time
import threading
import signal
from os import getpid
import traceback
from random import getrandbits
#from toolkit.benchmarking.benchmark import benchmark
from network_tools.rpc.base_classes.ServerProviderBase import \
    ServerProviderBase
from network_tools.rpc.shared_memory.shm_socket.ResponseSHMSocket import \
    ResponseSHMSocket
from network_tools.rpc.shared_memory.shm_socket.RequestSHMSocket import \
    RequestSHMSocket
from network_tools.rpc.shared_memory.kill_thread import kill_thread


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
        self.shutdown_ok = False

        self.DResponseSHMSockets = {}
        t1 = threading.Thread(target=self.__reap_client_sockets, args=())
        t1.start()
        t2 = self.serve_thread_loop = threading.Thread(target=self.__main, args=())
        t2.start()
        #_thread.start_new_thread(self.__reap_client_sockets, ())
        #_thread.start_new_thread(self.__main, ())
        return self

    def shutdown(self):
        self.shut_me_down = True
        t_from = time.time()
        while not self.shutdown_ok:
            time.sleep(0.05)
            if time.time()-t_from > 5:
                print(f"Trying to send shutdown command to SHMServer which is in state: {self.STATE}")
                #kill_thread(self.serve_thread_loop)
                from network_tools.rpc.shared_memory.SHMClient import SHMClient
                client = SHMClient(self.server_methods, self.port)
                shutdown_ok = False
                for x in range(10000):
                    xx = client.send(b'shutdown', str(getpid()).encode('ascii'))
                    print("SHUTDOWN RESPONSE:", xx)
                    if xx == b'ok':
                        print(f"Thread shutdown OK pid [{getpid()}]")
                        shutdown_ok = True
                        break

                if not shutdown_ok:
                    print(f"SHUTDOWN NOT OK!!! pid [{getpid()}]")
                    time.sleep(1)
                    raise Exception(f"SHUTDOWN NOT OK!!! pid [{getpid()}]")
                time.sleep(1)
                break

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
        spin_next_time = 1

        while True:
            # TODO: Should there be better error handling here?
            # The trouble is, nothing should ever be allowed to
            # go wrong here - if it does, perhaps the server
            # should die anyway(?)
            #print(f"{self.server_methods.name}: "
            #      f"Getting from {self.request_socket.socket_name}")

            if self.shut_me_down:
                self.shutdown_ok = True
                print(f"Signal to shutdown SHMServer {self.name} in worker thread caught: returning")
                return

            try:
                try:
                    self.STATE = 'waiting for command'
                    echo_me, cmd, args, client_id = self.request_socket.get(
                        timeout=1, spin=spin_next_time
                    )
                    spin_next_time = 1
                except TimeoutError:
                    spin_next_time = 0
                    continue

                self.STATE = f'getting response socket for {client_id}'
                response_socket = self.__get_response_socket(client_id)
                #print(f"{self.server_methods.name}:{self.server_methods.port} "
                #      f"Handling command:", cmd, args)

                if cmd == b'heartbeat':
                    self.STATE = 'heartbeat'
                    try:
                        response_socket.put(echo_me, b'+'+args, timeout=20)
                    except:
                        traceback.print_exc()
                elif cmd == b'shutdown':
                    shutdown_pid = int(args)
                    if shutdown_pid == getpid():
                        self.STATE = 'shutdown'
                        response_socket.put(echo_me, b'+ok', timeout=20)
                        raise SystemExit(f"Shutdown requested for SHMServer {self.name}")
                    else:
                        self.STATE = 'ignore shutdown'
                        response_socket.put(echo_me, b'+mismatch:%s!=%s' % (getpid(), shutdown_pid), timeout=20)
                else:
                    self.STATE = f'handling command {cmd}'
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

                    self.STATE = f'sending response for command {cmd}'
                    try:
                        response_socket.put(echo_me, send_data, timeout=20)
                    except:
                        traceback.print_exc()
            except:
                traceback.print_exc()
                time.sleep(1)

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
