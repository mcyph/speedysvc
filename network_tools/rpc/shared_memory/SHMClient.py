import time
import _thread
from collections import Counter
from toolkit.documentation.copydoc import copydoc
from network_tools.rpc.base_classes.ClientProviderBase import ClientProviderBase
from network_tools.rpc.shared_memory.shm_socket.SHMSocket import SHMSocket, int_struct


DPortCounter = Counter()


class SHMClient(ClientProviderBase):
    def __init__(self, server_methods, port=None):
        """

        :param server_methods:
        """
        if port is None:
            port = server_methods.port
        self.port = port

        ClientProviderBase.__init__(self, server_methods, port)

        self.__create_conn_to_server()
        self.lock = _thread.allocate()
        _thread.start_new_thread(self.__periodic_heartbeat, ())

        if DPortCounter.get(port):
            import warnings
            warnings.warn(
                f"Client started more than once for port {port}: "
                f"is this necessary?"
            )
        DPortCounter[port] += 1

    def __del__(self):
        DPortCounter[self.port] -= 1

    def __periodic_heartbeat(self):
        while 1:
            if self.to_server_socket.get_sockets_destroyed():
                print("To server socket destroyed; attempting to recreate")
                self.__create_conn_to_server()

            if self.from_server_socket.get_sockets_destroyed():
                # Should never get here, I think(?)
                print("From server socket destroyed; attempting to recreate")
                self.__create_conn_to_server()

            #try:
            #    self.send('heartbeat', str(time.time()).encode('ascii'))
            #except:
            #    print("Heartbeat failed; attempting to recreate connection")
            #    self.__create_conn_to_server()

            time.sleep(3)

    def __create_conn_to_server(self):
        # Acquire a lock to the server(s)
        self.client_id = self._acquire_lock()
        self.client_id_as_bytes = int_struct.pack(self.client_id)

        # Create a connection to the server(s)
        self.to_server_socket = SHMSocket(
            socket_name='to_server_%s' % self.port,
            init_resources=False
        )
        # Create a connection that the server can use to talk to us
        self.from_server_socket = SHMSocket(
            socket_name='from_server_%s_%s' % (self.port, self.client_id),
            init_resources=True
        )

    @copydoc(ClientProviderBase.send)
    def send(self, fn, data, timeout=60):
        with self.lock:
            data = fn.serialiser.dumps(data)
            self.to_server_socket.put(
                self.client_id_as_bytes+
                fn.__name__.encode('ascii')+b' '+data,
                timeout=10
            )
            data = self.from_server_socket.get(timeout=timeout)

            if data[0] == b'+'[0]:
                # An "ok" response
                data = fn.serialiser.loads(data[1:])
                return data
            elif data[0] == b'-'[0]:
                # An exception occurred
                raise Exception(data[1:])
            else:
                raise Exception("Invalid response code: %s" % data[0])


if __name__ == '__main__':
    import time
    from random import randint

    def run():
        t = time.time()
        inst = SHMClient(5555)

        for x in range(100000):
            #print('SEND:', i)
            #for inst in LInsts:
            i = str(randint(0, 9999999999999)).encode('ascii')*50
            data = inst.send('echo', i)
            assert data == i, (data, i)

            if x % 10000 == 0:
                print(data)

        print(time.time()-t)

    import multiprocessing
    LProcesses = []
    for x in range(12):
        process = multiprocessing.Process(target=run)
        LProcesses.append(process)
        process.start()
    while 1: time.sleep(1)
