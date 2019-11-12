import mmap
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
                 clean_up=False,
                 msg_size=MSG_SIZE):

        self.socket_name = socket_name
        self.clean_up = clean_up

        if clean_up:
            # Clean up since last time
            try: posix_ipc.unlink_shared_memory(socket_name)
            except: pass
            try: posix_ipc.unlink_semaphore(socket_name)
            except: pass

            # Create the shared memory and the semaphore,
            # and map it with mmap
            self.memory = memory = posix_ipc.SharedMemory(
                socket_name,
                posix_ipc.O_CREX,
                size=msg_size
            )
            self.write_semaphore = write_semaphore = posix_ipc.Semaphore(
                socket_name+'_write',
                posix_ipc.O_CREX
            )
            self.read_semaphore = read_semaphore = posix_ipc.Semaphore(
                socket_name+'_read',
                posix_ipc.O_CREX
            )
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        else:
            # Same as above, but don't use in "create" mode as we're
            # connecting to a semaphore/shared memory that
            # (should've been) already created.
            self.memory = memory = posix_ipc.SharedMemory(socket_name)
            self.write_semaphore = write_semaphore = \
                posix_ipc.Semaphore(socket_name+'_write')
            self.read_semaphore = read_semaphore = \
                posix_ipc.Semaphore(socket_name+'_read')
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        # We (apparently) don't need the file
        # descriptor after it's been memory mapped
        memory.close_fd()

        # Make it so that the write semaphore is incremented by 1,
        # so we can initially write to the semaphore
        # (but don't increment the read semaphore,
        #  as nothing is in the queue yet!)
        write_semaphore.release()

    def __del__(self):
        """
        Clean up
        """
        self.mapfile.close()

        if self.clean_up:
            # Only clear out the memory/
            # semaphore if in server mode
            self.memory.unlink()
            self.read_semaphore.unlink()
            self.write_semaphore.unlink()

    def put(self, data: bytes):
        """
        Put an item into the (single-item) queue
        :param data: the data as a string of bytes
        """
        while self.read_semaphore.value:
            # Don't allow writes if the existing value hasn't
            # been collected! Hopefully this'll happen rarely enough
            # (should only happen from multiple processes writing to
            # the queue at once) that it won't matter performance/
            # concurrency-wise
            time.sleep(0.0001)

        # WARNING: something could "put" here!

        with self.write_semaphore:
            self.mapfile[0:int_struct.size] = int_struct.pack(len(data))
            self.mapfile[int_struct.size:int_struct.size+len(data)] = data

            # Let the data be read
            self.read_semaphore.release()

    def get(self):
        """
        Get/pop an item from the (single-item) queue
        :return: the item from the queue
        """

        # Make sure can't be written to while we're reading!
        with self.write_semaphore:
            # Make it so the data can no longer be read
            # DEADLOCK WARNING!!! ========================================================================
            self.read_semaphore.acquire()

            amount = int_struct.unpack(self.mapfile[0:int_struct.size])[0]
            data = self.mapfile[int_struct.size:int_struct.size+amount]
            self.mapfile[0:int_struct.size] = int_struct.pack(ALL_DATA_RECEIVED)
            return data


if __name__ == '__main__':
    import time

    server_socket = SHMSocket('q', clean_up=True)
    client_socket = SHMSocket('q')
    DATA = b'my ranadasdmsak data'

    from_t = time.time()
    for x in range(500000):
        server_socket.put(DATA)
        assert client_socket.get() == DATA
    print(time.time()-from_t)
