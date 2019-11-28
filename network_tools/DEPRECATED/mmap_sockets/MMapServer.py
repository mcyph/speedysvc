import os
import re
import mmap
import time
import fcntl
import _thread
import msgpack
import setproctitle
from glob import glob
from json import dumps, loads

from network_tools.mmap_sockets.Base import Base
from toolkit.io.shm_ctypes import shm_open, shm_unlink

DEBUG = True


def json_method(fn):
    fn.is_json = True
    return fn


def msgpack_method(fn):
    fn.is_msgpack = True
    return fn


class MMapServer(Base):
    def __init__(self, DCmds, port):
        def greet(data):
            #print("GREET!")
            return b'ok'

        DCmds.update({
            'greet': greet
        })
        self.DCmds = DCmds
        # A "port", to allow uniquely identifying a specific service
        # I'm using only a number here, to allow portability with
        # other kinds of RPC later.
        self.port = port

        self.update_process_name()
        self.lockfile = self.acquire_lock()
        self.clean_mmap_files()

        self.num_threads = 1
        _thread.start_new_thread(self.main, (0,))

    def update_process_name(self):
        """
        Change the process name to be that of the subclass name,
        so as to be able to track memory usage in task managers
        :return: None
        """
        setproctitle.setproctitle(
            ("mmap" + self.__class__.__name__.lower())[:15]
        )

    def acquire_lock(self):
        path = self.PATH % (self.port, 'serverlock')
        lockfile = open(path, "a+")

        try:
            fcntl.flock(
                lockfile.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB
            )
        except IOError:
            raise SystemExit(
                "Can't acquire lock file %s: "
                    "is another instance already running?" % path
            )
        return lockfile

    def clean_mmap_files(self):
        # Clean up previous files
        for path in glob(self.PATH % (self.port, '*')):
            os.unlink(path)

    def main(self, thread_num):
        print('Starting new server thread:', thread_num)

        # Open the file, and zero out the data
        path = self.PATH % (self.port, thread_num)
        fd = os.open(path, os.O_CREAT|os.O_TRUNC|os.O_RDWR)

        mmap_file_size = self.INITIAL_MMAP_FILE_SIZE
        assert os.write(fd, b'\x00' * mmap_file_size) == mmap_file_size

        mmap_buf = mmap.mmap(
            fd, mmap_file_size,
            mmap.MAP_SHARED,
            mmap.PROT_WRITE|mmap.PROT_READ
        )
        mmap_vars = (
            Base.get_variables(self, mmap_buf)
        )

        # Assign some communication values locally
        t = time.time()

        while 1:
            if mmap_vars.cur_state_int.value == self.STATE_CMD_TO_SERVER:
                mmap_file_size, mmap_vars = self._handle_cmd(
                    thread_num, mmap_buf,  mmap_file_size, mmap_vars
                )
                t = time.time()

            i_t = time.time() - t
            if i_t > 1:
                time.sleep(0.05)
            elif i_t > 0.1:
                time.sleep(0.001)

    def _handle_cmd(self, thread_num, mmap_buf,
                    mmap_file_size, mmap_vars):
        if (
            thread_num+1 == self.num_threads and
            self.num_threads+1 < self.MAX_CONNECTIONS
        ):
            # Start a new thread the first time this one receieves a
            # command, to allow for additional connections
            self.num_threads += 1
            _thread.start_new_thread(self.main, (self.num_threads-1,))
        #else:
            #print("HANDLE:", thread_num+1, self.num_threads)

        # Get the command/command argument from the client
        recv_data = mmap_buf[
            mmap_vars.DATA_OFFSET:
            mmap_vars.DATA_OFFSET+mmap_vars.amount_int.value
        ]
        cmd, _, recv_data = recv_data.partition(b' ')

        # Get the data to send from the callable
        fn = self.DCmds[cmd.decode('ascii')]

        try:
            if hasattr(fn, 'is_json'):
                # Use JSON if method defined using @json_method
                send_data = b'+'+dumps(self.DCmds[cmd.decode('ascii')](
                    *loads(recv_data.decode('utf-8'))
                )).encode('utf-8')
            elif hasattr(fn, 'is_msgpack'):
                # Use msgpack
                send_data = b'+' + msgpack.dumps(
                    self.DCmds[cmd.decode('ascii')](
                        **msgpack.loads(
                            recv_data,
                            encoding='utf-8',
                            use_bin_type=True
                        )
                    )
                )
            else:
                # Otherwise use raw data
                send_data = b'+'+self.DCmds[cmd.decode('ascii')](recv_data)

        except Exception as exc:
            # Just send a basic Exception instance for now, but would be nice
            # if could recreate some kinds of exceptions on the other end
            send_data = b'-'+repr(exc).encode('utf-8')
            import traceback
            traceback.print_exc()

        if DEBUG:
            assert isinstance(send_data, bytes), (cmd, repr(send_data))

        # Resize the mmap if data is too large for it
        if len(send_data) > (mmap_file_size - mmap_vars.DATA_OFFSET):
            mmap_file_size = int(len(send_data) * 1.5)
            mmap_file_size -= mmap_file_size % mmap.PAGESIZE
            print('RESIZE MMAP:', mmap_file_size, len(send_data))
            mmap_buf.resize(mmap_file_size)

            # These variables are c pointers which
            # become invalid after a resize
            mmap_vars = (
                Base.get_variables(self, mmap_buf)
            )

        # Send the data
        mmap_buf[
            mmap_vars.DATA_OFFSET:
            mmap_vars.DATA_OFFSET+len(send_data)
        ] = send_data
        mmap_vars.amount_int.value = len(send_data)

        if DEBUG:
            # This might be overkill, but just to be sure...
            assert mmap_buf[
                mmap_vars.DATA_OFFSET:
                mmap_vars.DATA_OFFSET+len(send_data)
            ] == send_data
            assert mmap_vars.amount_int.value == len(send_data)

        # Tell the client it can receive data
        mmap_vars.cur_state_int.value = self.STATE_DATA_TO_CLIENT
        return mmap_file_size, mmap_vars


if __name__ == '__main__':
    inst = MMapServer({
        'echo': lambda data: data
    }, port=5555)

    while 1:
        time.sleep(1)
