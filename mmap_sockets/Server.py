import os
import mmap
import time
import thread

from Base import Base


class Server(Base):
    def __init__(self, DCmds):
        self.DCmds = DCmds

        for x in xrange(self.MAX_CONNECTIONS):
            thread.start_new_thread(self.main, (x,))


    def main(self, thread_num):
        # Open the file, and zero out the data
        path = self.PATH % thread_num
        fd = os.open(path, os.O_CREAT|os.O_TRUNC|os.O_RDWR)
        sz = 1048576*100 # 100MB
        sz -= sz % mmap.PAGESIZE
        assert os.write(fd, '\x00' * sz) == sz

        buf = mmap.mmap(
            fd, sz,
            mmap.MAP_SHARED,
            mmap.PROT_WRITE|mmap.PROT_READ
        )
        Base.__init__(self, buf)


        # Assign some communication values locally
        cur_state_int = self.cur_state_int
        amount_int = self.amount_int
        DATA_OFFSET = self.DATA_OFFSET


        x = 1
        sleep_every = self.SLEEP_EVERY

        while 1:
            if cur_state_int.value == self.STATE_CMD_TO_SERVER:
                # Get the command/command argument from the client
                recv_data = buf[DATA_OFFSET:DATA_OFFSET+amount_int.value]
                cmd, _, recv_data = recv_data.partition(' ')

                # Send a response to the client
                send_data = self.DCmds[cmd](recv_data)
                buf[DATA_OFFSET:DATA_OFFSET+len(send_data)] = send_data
                amount_int.value = len(send_data)
                assert amount_int.value == len(send_data)

                cur_state_int.value = self.STATE_DATA_TO_CLIENT
                x = 1
                sleep_every = self.SLEEP_EVERY


            if x % sleep_every == 0:
                time.sleep(0.001)
                if sleep_every > 1:
                    sleep_every //= self.SLEEP_DIV_BY
            else:
                x += 1


if __name__ == '__main__':
    inst = Server({
        'echo': lambda data: data
    })

    while 1:
        time.sleep(1)
