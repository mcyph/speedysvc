import sys, os
import mmap
import time
import thread
from toolkit.file_locks import lock, unlock, LockException, LOCK_NB, LOCK_EX

from Base import Base


def set_exit_handler(func):
    if os.name == "nt":
        try:
            import win32api
            win32api.SetConsoleCtrlHandler(func, True)
        except ImportError:
            version = '.'.join(map(str, sys.version_info[:2]))
            raise Exception('pywin32 not installed for Python ' + version)
    else:
        import signal
        signal.signal(signal.SIGABRT, func)
        signal.signal(signal.SIGTERM, func)


class Client(Base):
    def __init__(self):
        self.thread_lock = thread.allocate_lock()

        # Open the file for reading
        path = self.path = self.PATH % self._acquire_lock()
        while 1:
            try:
                fd = self.fd = os.open(path, os.O_RDWR)
                break
            except OSError:
                time.sleep(1)
                print 'Server not ready. Trying again in 1 seconds...'
                continue

        # Memory map the file
        file_size = self.file_size = os.path.getsize(path)
        buf = self.buf = mmap.mmap(
            fd, file_size,
            mmap.MAP_SHARED,
            mmap.PROT_READ|mmap.PROT_WRITE
        )

        self.cur_state_int, self.amount_int, self.DATA_OFFSET = (
            Base.get_variables(self, buf)
        )

        set_exit_handler(self._release_lock)
        self.cur_state_int.value = self.STATE_DATA_TO_CLIENT


    def __del__(self):
        self._release_lock()


    def _release_lock(self):
        try:
            unlock(self.lock_file)
        except:
            pass


    #=================================================================#
    #                     Shared Resource Methods                     #
    #=================================================================#


    def _acquire_lock(self):
        print 'Acquire mmap lock:',

        x = 0
        while 1:
            lock_file_path = self.lock_file_path = (
                self.PATH % (str(x)+'.lock')
            )

            lock_file = open(lock_file_path, "a+")

            try:
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

            print 'Lock %s acquired!' % x
            self.lock_file = lock_file
            return x

        raise Exception("No available connections!")


    def send(self, cmd, data):
        """
        cmd -> one of CMD_GET, CMD_PUT, CMD_ITER_STARTSWITH
        DParams -> any parameters to be sent via
        """
        with self.thread_lock:
            send_me = '%s %s' % (cmd, data)
            DATA_OFFSET = self.DATA_OFFSET

            self.buf[DATA_OFFSET:DATA_OFFSET+len(send_me)] = send_me
            self.amount_int.value = len(send_me)
            # This might be overkill, but just to be sure...
            assert self.buf[DATA_OFFSET:DATA_OFFSET+len(send_me)] == send_me
            assert self.amount_int.value == len(send_me)

            self.cur_state_int.value = self.STATE_CMD_TO_SERVER
            return self.__recv()


    def __recv(self):
        t = time.time()
        DATA_OFFSET = self.DATA_OFFSET
        sleep = time.sleep

        while 1:
            cur_state = self.cur_state_int.value

            if cur_state == self.STATE_DATA_TO_CLIENT:
                amount = self.amount_int.value
                self.__resize_mmap_if_needed(amount)

                data = self.buf[DATA_OFFSET:DATA_OFFSET+amount]
                break

            i_t = time.time()-t
            if i_t > 1:
                sleep(0.05)
            elif i_t > 0.1:
                sleep(0.001)

        return data


    def __resize_mmap_if_needed(self, amount):
        # Resize the buffer if data is more
        # than the currently mmapped area
        if amount+self.DATA_OFFSET > self.file_size:
            file_size = self.file_size = os.path.getsize(self.path)
            print 'RESIZE MMAP:', file_size
            self.buf.resize(file_size)

            self.cur_state_int, self.amount_int, self.DATA_OFFSET = (
                Base.get_variables(self, self.buf)
            )


if __name__ == '__main__':
    from random import randint

    inst = Client()
    t = time.time()
    for x in xrange(1000000):
        i = str(randint(0, 5000000))*500
        #print 'SEND:', i
        assert inst.send('echo', i) == i

    print time.time()-t
