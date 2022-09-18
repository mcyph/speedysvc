from typing import Optional
from ast import literal_eval
from abc import ABC, abstractmethod

from speedysvc.toolkit.exceptions.exception_map import DExceptions
from speedysvc.toolkit.io.file_locks import lock, unlock, LockException, LOCK_NB, LOCK_EX


class ClientProviderBase(ABC):
    def __init__(self,
                 service_port: Optional[int] = None,
                 service_name: Optional[str] = None):
        self.service_port = service_port
        self.service_name = service_name

    PATH = '/tmp/shmsrv-%s-%s'
    MAX_CONNECTIONS = 500

    def _acquire_lock(self):
        #print('Acquire shm lock:', end=' ')

        x = 0
        while True:
            self.lock_file_path = self.PATH % (self.service_port, f'{x}.clientlock')
            lock_file = open(self.lock_file_path, "a+")

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
