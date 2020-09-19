from ast import literal_eval
from abc import ABC, abstractmethod
from speedysvc.toolkit.exceptions.exception_map import DExceptions
from speedysvc.toolkit.io.file_locks import lock, unlock, LockException, LOCK_NB, LOCK_EX


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
        #print('Acquire shm lock:', end=' ')

        x = 0
        while True:
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

            #print('Lock %s acquired!' % x)
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

    def _handle_exception(self, response_data):
        """

        :param response_data:
        :return:
        """
        response_data = response_data[1:].decode('utf-8', errors='replace')
        if '(' in response_data:
            exc_type, _, remainder = response_data[:-1].partition('(')
            try:
                # Try to convert to python types the arguments (safely)
                # If we can't, it's not the end of the world
                remainder = literal_eval(remainder)
            except:
                pass
        else:
            remainder = ''
            exc_type = None

        if exc_type is not None and exc_type in DExceptions:
            raise DExceptions[exc_type](remainder)
        else:
            raise Exception(response_data)
