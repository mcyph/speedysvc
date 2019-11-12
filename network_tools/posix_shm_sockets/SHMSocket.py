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
    def __init__(self, socket_name, clean_up=False, msg_size=MSG_SIZE):
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
            self.semaphore = semaphore = posix_ipc.Semaphore(
                socket_name,
                posix_ipc.O_CREX
            )
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        else:
            # Same as above, but don't use in "create" mode as we're
            # connecting to a semaphore/shared memory that
            # (should've been) already created.
            self.memory = memory = posix_ipc.SharedMemory(socket_name)
            self.semaphore = semaphore = posix_ipc.Semaphore(socket_name)
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        # We (apparently) don't need the file
        # descriptor after it's been memory mapped
        memory.close_fd()

        # Make it so that the semaphore is incremented by 1
        semaphore.release()

    def __del__(self):
        # Clean up
        self.mapfile.close()

        if self.clean_up:
            # Only clear out the memory/
            # semaphore if in server mode
            self.memory.unlink()
            #posix_ipc.unlink_shared_memory('server_queue')
            self.semaphore.unlink()

    def put(self, data: bytes):
        """
        Put an item into the (single-item) queue
        :param data: the data as a string of bytes
        """
        with self.semaphore:
            self.mapfile[0:int_struct.size] = int_struct.pack(len(data))
            self.mapfile[int_struct.size:int_struct.size+len(data)] = data

    def get(self):
        """
        Get/pop an item from the (single-item) queue
        :return: the item from the queue
        """
        with self.semaphore:
            amount = int_struct.unpack(
                self.mapfile[0:int_struct.size]
            )[0]
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
