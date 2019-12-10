from abc import ABC, abstractmethod
from toolkit.io.file_locks import lock, unlock, LockException, LOCK_NB, LOCK_EX


class ClientProviderBase(ABC):
    def __init__(self, server_methods=None, port=None):
        #assert isinstance(server_methods, ServerMethodsBase)
        if port is None:
            port = server_methods.port
        self.port = port
        self.server_methods = server_methods

    def get_server_methods(self):
        return self.server_methods

    PATH = '/tmp/shmsrv-%s-%s'
    MAX_CONNECTIONS = 500

    def _acquire_lock(self):
        """
        TODO: Make me generic between implementations!! ==================================================

        :return:
        """
        print('Acquire shm lock:', end=' ')

        x = 0
        while 1:
            lock_file_path = self.lock_file_path = self.PATH % (
                self.port, str(x) + '.clientlock'
            )
            lock_file = open(lock_file_path, "a+")

            try:
                # print("Trying to lock:", x)
                lock(lock_file, LOCK_EX | LOCK_NB)
            except (LockException, IOError):
                try:
                    lock_file.close()
                except:
                    pass

                x += 1
                if x > self.MAX_CONNECTIONS:
                    raise Exception('too many connections!')
                continue

            print('Lock %s acquired!' % x)
            self.lock_file = lock_file
            return x

        raise Exception("No available connections!")

    @abstractmethod
    def send(self, cmd, data):
        """
        Send the command `cmd` to the RPC server.
        Encodes data with the relevant serialiser.
        (JSON/raw bytes etc), before decoding the
        data with the same serialiser.

        :param cmd: the name of the RPC method,
                    as ascii characters
        :param data: the parameters of the RPC
                     method to send to the server
        :return: depends on what the RPC returns - could
                 be almost anything that's encodable
        """
        pass
