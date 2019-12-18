import mmap
import time
from abc import ABC, abstractmethod
from hybrid_lock import HybridSpinSemaphore, \
    CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE
import posix_ipc
from network_tools.rpc.shared_memory.shared_params import MSG_SIZE


class SHMSocketBase(ABC):
    def __init__(self,
                 socket_name, init_resources=False,
                 msg_size=MSG_SIZE):
        """
        A single-directional "socket"-like object, which provides
        sequential shared memory-based "pipes", synchronised
        by a hybrid spinlocks/named semaphores.

        This provides extremely high throughput, extremely
        low latency IPC, which should largely be
        limited by the speed of serialisation/deserialisation,
        and the python interpreter.

        Note that after a process which initialised the resources
        has exited abnormally (e.g. due to a segfault), the shared
        memory and semaphore can still exist on the OS.

        :param socket_name: a unique identifier. Needs to be of type
                            `bytes` (not `str`).
        :param init_resources: whether to overwrite the socket at
                               identifier `socket_name` if it exists.
                               Also will clean up this socket when
                               this process exists.
        :param msg_size: the maximum message size in bytes
                         (the amount of shared memory that will
                          be allocated).
        """

        if msg_size < 400:
            # We'll set the limit somewhat arbitrarily - it needs to be
            # around this amount or could be trouble with sending
            # commands of 255, or just not be that useful as
            # performance gets lower the lower this number.
            raise ValueError("Message size (buffer) for shared "
                             "memory must be more than 400 in length")

        # NOTE: ntc stands for "nothing to collect"
        # and rtc stands for "ready to collect"
        # having 2 semaphores like this allows for blocking
        # operations between the put/get operations

        self.socket_name = socket_name
        self.init_resources = init_resources
        self.last_used_time = time.time()

        rtc_bytes = (socket_name + '_rtc').encode('ascii')
        ntc_bytes = (socket_name + '_ntc').encode('ascii')

        if init_resources:
            # Clean up since last time
            try: posix_ipc.unlink_shared_memory(socket_name)
            except: pass

            # Create the shared memory and the semaphore,
            # and map it with mmap
            self.memory = memory = posix_ipc.SharedMemory(
                socket_name, posix_ipc.O_CREX, size=msg_size
            )
            self.mapfile = mmap.mmap(memory.fd, memory.size)

            # Make it so that the write semaphore is incremented by 1,
            # so we can initially write to the semaphore
            # (but don't increment the read semaphore,
            #  as nothing is in the queue yet!)

            self.rtc_mutex = HybridSpinSemaphore(
                rtc_bytes, CREATE_NEW_OVERWRITE,
                initial_value=0
            )
            self.ntc_mutex = HybridSpinSemaphore(
                ntc_bytes, CREATE_NEW_OVERWRITE,
                initial_value=1
            )

            assert self.rtc_mutex.get_value() == 0, \
                self.rtc_mutex.get_value()
            assert self.ntc_mutex.get_value() == 1, \
                self.ntc_mutex.get_value()
        else:
            # Same as above, but don't use in "create" mode as we're
            # connecting to a semaphore/shared memory that
            # (should've been) already created.
            self.memory = memory = posix_ipc.SharedMemory(socket_name)
            self.mapfile = mmap.mmap(memory.fd, memory.size)

            self.rtc_mutex = HybridSpinSemaphore(
                rtc_bytes, CONNECT_TO_EXISTING,
                initial_value=0
            )
            self.ntc_mutex = HybridSpinSemaphore(
                ntc_bytes, CONNECT_TO_EXISTING,
                initial_value=1
            )

        #print(
        #    f"{self.socket_name} - "
        #    "Ready to collect:", self.rtc_mutex.get_value(),
        #    "Nothing to collect:", self.ntc_mutex.get_value()
        #)

        # We (apparently) don't need the file
        # descriptor after it's been memory mapped
        memory.close_fd()

    def log(self, *msgs):
        print(f'{self.socket_name}:', *msgs)

    def get_num_parts(self, part_size, response_len):
        return (
           (
                response_len - (response_len % part_size)
           ) // part_size
        ) + 1

    def __del__(self):
        """
        Clean up
        """
        if hasattr(self, 'mapfile'):
            self.mapfile.close()

        if self.init_resources:
            # Only clear out the memory/
            # mutexes if we created them
            self.memory.unlink()

            self.rtc_mutex.destroy()
            self.ntc_mutex.destroy()
        else:
            # Otherwise just close the mutexes
            del self.rtc_mutex
            del self.ntc_mutex

    @abstractmethod
    def put(self, data, timeout):
        """
        To be implemented in subclasses.

        Note that subclasses may violate Liskov Substitution
        Principle here slightly, as put has different parameters
        depending on whether a command request or response is
        being sent.

        While not 100% desirable, this is the best solution I
        can come up with.
        """
        pass

    @abstractmethod
    def get(self, timeout):
        """
        To be implemented in subclasses.
        """
        pass

    def get_sockets_destroyed(self):
        """
        Get whether either the "ready to collect" or
        "nothing to collect" locks have been destroyed.

        This is the only way to check whether the remote
        server/client has destroyed one or both the locks.

        :return: True/False
        """
        return self.rtc_mutex.get_destroyed() or \
               self.ntc_mutex.get_destroyed()

    def get_last_used_time(self):
        """
        Get the float unix timestamp when this socket
        was last used (a get or put operation was performed).

        :return: a float unix timestamp
        """
        return self.last_used_time


if __name__ == '__main__':
    import time

    server_socket = SHMSocketBase('q', init_resources=True)
    client_socket = SHMSocketBase('q')
    DATA = b'my ranadasdmsak data'*20

    from_t = time.time()
    for x in range(1000000):
        server_socket.put(DATA)
        assert client_socket.get() == DATA
    print(time.time()-from_t)
