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
                 msg_size=MSG_SIZE):

        self.socket_name = socket_name
        self.init_resources = init_resources
        self.last_used_time = time.time()

        if init_resources:
            # Clean up since last time
            try: posix_ipc.unlink_shared_memory(socket_name)
            except: pass
            try: posix_ipc.unlink_semaphore(socket_name+'_write')
            except: pass
            try: posix_ipc.unlink_semaphore(socket_name+'_read')
            except: pass

            # Create the shared memory and the semaphore,
            # and map it with mmap
            self.memory = memory = posix_ipc.SharedMemory(
                socket_name,
                posix_ipc.O_CREX,
                size=msg_size
            )
            self.write_semaphore = write_semaphore = posix_ipc.Semaphore(
                socket_name+'_write', posix_ipc.O_CREX
            )
            self.read_semaphore = posix_ipc.Semaphore(
                socket_name+'_read', posix_ipc.O_CREX
            )
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        else:
            # Same as above, but don't use in "create" mode as we're
            # connecting to a semaphore/shared memory that
            # (should've been) already created.
            self.memory = memory = posix_ipc.SharedMemory(socket_name)
            self.write_semaphore = write_semaphore = posix_ipc.Semaphore(socket_name+'_write')
            self.read_semaphore = posix_ipc.Semaphore(socket_name+'_read')
            self.mapfile = mmap.mmap(memory.fd, memory.size)

        # Make it so that the write semaphore is incremented by 1,
        # so we can initially write to the semaphore
        # (but don't increment the read semaphore,
        #  as nothing is in the queue yet!)
        write_semaphore.release()

        # We (apparently) don't need the file
        # descriptor after it's been memory mapped
        memory.close_fd()

    def __del__(self):
        """
        Clean up
        """
        if hasattr(self, 'mapfile'):
            self.mapfile.close()

        # NOTE: The below was commented out, so as to allow
        # clients/servers reusing resources, and allow continuation
        # of sessions in many cases. Though this does leak a bit of
        # memory, I don't think 64kb blocks will make a big
        # difference considering how much memory modern systems have.
        """
        if self.init_resources:
            # Only clear out the memory/
            # semaphore if in server mode
            self.memory.unlink()
            self.read_semaphore.unlink()
            self.write_semaphore.unlink()
        """

    def put(self, data: bytes):
        """
        Put an item into the (single-item) queue
        :param data: the data as a string of bytes
        """
        self.last_used_time = time.time()

        while self.read_semaphore.value:
            # Don't allow writes if the existing value hasn't
            # been collected! Hopefully this'll happen rarely enough
            # (should only happen from multiple processes writing to
            # the queue at once) that it won't matter performance/
            # concurrency-wise
            time.sleep(0.0001)
            pass

        while True:
            with self.write_semaphore:
                # Something could "put" directly before the write semaphore!
                # While this should be rare, better safe than sorry
                if self.read_semaphore.value:
                    time.sleep(0.0001)
                    continue

                self.mapfile[0:int_struct.size] = int_struct.pack(len(data))
                self.mapfile[int_struct.size:int_struct.size+len(data)] = data

                # Let the data be read
                self.read_semaphore.release()
                break

    def get(self):
        """
        Get/pop an item from the (single-item) queue
        :return: the item from the queue
        """
        self.last_used_time = time.time()

        # Make sure can't be written to while we're reading!
        with self.write_semaphore:
            # Make it so the data can no longer be read
            # (and also wait for the data to actually become available)
            self.read_semaphore.acquire()

            amount = int_struct.unpack(self.mapfile[0:int_struct.size])[0]
            data = self.mapfile[int_struct.size:int_struct.size+amount]
            self.mapfile[0:int_struct.size] = int_struct.pack(ALL_DATA_RECEIVED)

        return data

    def get_last_used_time(self):
        return self.last_used_time


if __name__ == '__main__':
    import time

    server_socket = SHMSocket('q', init_resources=True)
    client_socket = SHMSocket('q')
    DATA = b'my ranadasdmsak data'*20

    from_t = time.time()
    for x in range(500000):
        server_socket.put(DATA)
        assert client_socket.get() == DATA
    print(time.time()-from_t)
