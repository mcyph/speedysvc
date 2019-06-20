import os
import mmap
import time
import _thread

from .Base import Base


class Server(Base):
    def __init__(self, DCmds, port):
        self.DCmds = DCmds
        # A "port", to allow uniquely identifying a specific service
        # I'm using only a number here, to allow portability with
        # other kinds of RPC later.
        self.port = port

        self.num_threads = 1
        _thread.start_new_thread(self.main, (0,))

    def main(self, thread_num):
        print('Starting new server thread:', thread_num)

        # Open the file, and zero out the data
        path = self.PATH % (self.port, thread_num)
        fd = os.open(path, os.O_CREAT|os.O_TRUNC|os.O_RDWR)
        sz = 10485760 # 10MB
        sz -= sz % mmap.PAGESIZE
        assert os.write(fd, '\x00' * sz) == sz

        buf = mmap.mmap(
            fd, sz,
            mmap.MAP_SHARED,
            mmap.PROT_WRITE|mmap.PROT_READ
        )
        cur_state_int, amount_int, DATA_OFFSET = (
            Base.get_variables(self, buf)
        )

        # Assign some communication values locally
        t = time.time()

        while 1:
            if cur_state_int.value == self.STATE_CMD_TO_SERVER:

                if (
                    thread_num+1 == self.num_threads and
                    self.num_threads+1 < self.MAX_CONNECTIONS
                ):
                    self.num_threads += 1
                    _thread.start_new_thread(self.main, (self.num_threads-1,))

                # Get the command/command argument from the client
                recv_data = buf[DATA_OFFSET:DATA_OFFSET+amount_int.value]
                cmd, _, recv_data = recv_data.partition(' ')

                # Send a response to the client
                send_data = self.DCmds[cmd](recv_data)
                #assert isinstance(send_data, str), (cmd, repr(send_data))

                # Resize the mmap if data is too large for it
                if len(send_data) > (sz-DATA_OFFSET):
                    sz = int(len(send_data) * 1.5)
                    sz -= sz % mmap.PAGESIZE
                    print('RESIZE MMAP:', sz, len(send_data))
                    buf.resize(sz)

                    # These variables are c pointers which
                    # become invalid after a resize
                    cur_state_int, amount_int, DATA_OFFSET = (
                        Base.get_variables(self, buf)
                    )

                buf[DATA_OFFSET:DATA_OFFSET+len(send_data)] = send_data
                amount_int.value = len(send_data)

                if False:
                    # This might be overkill, but just to be sure...
                    assert buf[DATA_OFFSET:DATA_OFFSET+len(send_data)] == send_data
                    assert amount_int.value == len(send_data)

                cur_state_int.value = self.STATE_DATA_TO_CLIENT
                t = time.time()

            i_t = time.time()-t
            if i_t > 1:
                time.sleep(0.05)
            elif i_t > 0.1:
                time.sleep(0.001)


if __name__ == '__main__':
    inst = Server({
        'echo': lambda data: data
    })

    while 1:
        time.sleep(1)
