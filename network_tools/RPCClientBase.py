from abc import ABC, abstractmethod
from toolkit.io.file_locks import lock, unlock, LockException, LOCK_NB, LOCK_EX


class RPCClientBase:
    def __init__(self, port):
        self.port = port

    PATH = '/tmp/shmsrv-%s-%s'
    MAX_CONNECTIONS = 500

    def _acquire_lock(self):
        print('Acquire shm lock:', end=' ')

        x = 0
        while 1:
            lock_file_path = self.lock_file_path = (
                self.PATH % (self.port, str(x)+'.clientlock')
            )
            lock_file = open(lock_file_path, "a+")

            try:
                #print("Trying to lock:", x)
                lock(lock_file, LOCK_EX|LOCK_NB)
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
    def send_json(self, cmd, data):
        pass

    @abstractmethod
    def send_msgpack(self, cmd, data):
        pass

    @abstractmethod
    def send(self, cmd, data):
        pass

