import os
import mmap
import time
import thread
from lockfile import LockFile, AlreadyLocked, NotLocked

from Base import Base


class Client(Base):
    def __init__(self):
        self.thread_lock = thread.allocate_lock()

        # Open the file for reading
        path = self.PATH % self._acquire_lock()
        fd = self.fd = os.open(path, os.O_RDWR)

        # Memory map the file
        buf = self.buf = mmap.mmap(
            fd, os.path.getsize(path),
            mmap.MAP_SHARED,
            mmap.PROT_READ|mmap.PROT_WRITE
        )
        Base.__init__(self, buf)

        self.DInfo = self.get('', {})


    def __del__(self):
        if hasattr(self, 'lock_file'):
            try:
                self.lock_file.release()
            except NotLocked:
                pass


    #=================================================================#
    #                     Shared Resource Methods                     #
    #=================================================================#


    def _acquire_lock(self):
        for x in xrange(self.NUM_PROCESSES):
            lock_file = LockFile(
                self.PATH % (str(x)+'.lockfile')
            )
            try:
                lock_file.acquire(0)
            except AlreadyLocked:
                continue

            self.lock_file = lock_file
            return x

        raise Exception("No available connections!")


    def recv(self):
        t = time.time()
        x = 1
        sleep_every = self.SLEEP_EVERY

        DATA_OFFSET = self.DATA_OFFSET


        while 1:
            cur_state = self.cur_state_int.value

            if cur_state not in self.SClientValues:
                amount = self.amount_int.value
                data = self.buf[DATA_OFFSET:DATA_OFFSET+amount]

                x = 1
                break


            if x % sleep_every == 0:
                time.sleep(0.001)
                if sleep_every > 1:
                    sleep_every //= self.SLEEP_DIV_BY
            else:
                x += 1


        print time.time()-t
        return cur_state, data


    def send(self, cmd, data):
        """
        cmd -> one of CMD_GET, CMD_PUT, CMD_ITER_STARTSWITH
        DParams -> any parameters to be sent via
        """
        send_me = '%s %s' % (cmd, data)
        DATA_OFFSET = self.DATA_OFFSET

        self.buf[DATA_OFFSET:DATA_OFFSET+len(send_me)] = send_me
        self.cur_state_int.value = self.STATE_CMD_TO_SERVER



if __name__ == '__main__':
    from random import randint

    inst = Client()
    while 1:
        i = randint(0, 5000000)
        inst.send(str(i))
        print i, inst.recv()
