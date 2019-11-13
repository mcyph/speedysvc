import mmap
import time
import struct
import posix_ipc
from network_tools.posix_shm_sockets.shared_params import MSG_SIZE

# Create an int encoder to allow encoding length
# and return client ID
int_struct = struct.Struct('i')

ALL_DATA_RECEIVED = -1
NO_MORE_DATA = -2


class SHMSocket:
    def __init__(self, socket_name,
                 init_resources=False,
                 msg_size=MSG_SIZE,
                 timeout=10):  # 10 seconds timeout

        # NOTE: ntc stands for "nothing to collect"
        # and rtc stands for "ready to collect"
        # having 2 semaphores like this allows for blocking
        # operations between the put/get operations

        self.socket_name = socket_name
        self.init_resources = init_resources
        self.last_used_time = time.time()
        self.timeout = timeout

        if init_resources:
            # Clean up since last time
            try: posix_ipc.unlink_shared_memory(socket_name)
            except: pass
            try: posix_ipc.unlink_semaphore(socket_name+'_rtc')
            except: pass
            try: posix_ipc.unlink_semaphore(socket_name+'_ntc')
            except: pass

            # Create the shared memory and the semaphore,
            # and map it with mmap
            self.memory = memory = posix_ipc.SharedMemory(
                socket_name,
                posix_ipc.O_CREX,
                size=msg_size
            )
            self.rtc_semaphore = write_semaphore = posix_ipc.Semaphore(
                socket_name+'_rtc', posix_ipc.O_CREX
            )
            self.ntc_semaphore = posix_ipc.Semaphore(
                socket_name+'_ntc', posix_ipc.O_CREX
            )
            self.mapfile = mmap.mmap(memory.fd, memory.size)

            # Make it so that the write semaphore is incremented by 1,
            # so we can initially write to the semaphore
            # (but don't increment the read semaphore,
            #  as nothing is in the queue yet!)
            self.ntc_semaphore.release()
            assert not self.rtc_semaphore.value

        else:
            # Same as above, but don't use in "create" mode as we're
            # connecting to a semaphore/shared memory that
            # (should've been) already created.
            self.memory = memory = posix_ipc.SharedMemory(socket_name)
            self.rtc_semaphore = write_semaphore = posix_ipc.Semaphore(socket_name+'_rtc')
            self.ntc_semaphore = posix_ipc.Semaphore(socket_name+'_ntc')
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        # We (apparently) don't need the file
        # descriptor after it's been memory mapped
        memory.close_fd()

    def log(self, *msgs):
        print(f'{self.socket_name}:', *msgs)

    def __del__(self):
        """
        Clean up
        """
        if hasattr(self, 'mapfile'):
            self.mapfile.close()

        if self.init_resources:
            # Only clear out the memory/
            # semaphore if we created them
            self.memory.unlink()
            self.rtc_semaphore.unlink()
            self.ntc_semaphore.unlink()

    def put(self, data: bytes, timeout=None):
        """
        Put an item into the (single-item) queue
        :param data: the data as a string of bytes
        """

        # It would be possible to make it so that there were lots of
        # different memory blocks, and the semaphore initially
        # incremented to the maximum value so as to (potentially)
        # allow for increased throughput.

        # TODO: Support very large queue items!!! ==============================================================

        self.last_used_time = time.time()
        self.ntc_semaphore.acquire(timeout)

        self.mapfile[0:int_struct.size] = int_struct.pack(len(data))
        self.mapfile[int_struct.size:int_struct.size+len(data)] = data

        # Let the data be read, signalling
        # data is "ready to collect"
        self.rtc_semaphore.release()

    def get(self, timeout=None):
        """
        Get/pop an item from the (single-item) queue
        :return: the item from the queue
        """
        self.last_used_time = time.time()
        self.rtc_semaphore.acquire(timeout)

        amount = int_struct.unpack(self.mapfile[0:int_struct.size])[0]
        data = self.mapfile[int_struct.size:int_struct.size+amount]

        # Signal there's "nothing to collect"
        # to allow future put operations
        self.ntc_semaphore.release()
        return data

    def get_last_used_time(self):
        return self.last_used_time


if __name__ == '__main__':
    import time

    server_socket = SHMSocket('q', init_resources=True)
    client_socket = SHMSocket('q')
    DATA = b'my ranadasdmsak data'*20

    from_t = time.time()
    for x in range(10000):
        server_socket.put(DATA)
        assert client_socket.get() == DATA
    print(time.time()-from_t)
