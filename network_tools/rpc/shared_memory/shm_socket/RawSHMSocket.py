import time
import struct
from network_tools.rpc.shared_memory.shm_socket.SHMSocket import \
    SHMSocketBase


# Create an int encoder to allow encoding length
# and return client ID
int_struct = struct.Struct('i')


class RawSHMSocket(SHMSocketBase):
    def put(self, data: bytes, timeout=3):
        """
        Put an item into the (single-item) queue
        :param data: the data as a string of bytes
        """

        # It would be possible to make it so that there were lots of
        # different memory blocks, and the semaphore initially
        # incremented to the maximum value so as to (potentially)
        # allow for increased throughput.

        # TODO: Support very large queue items!!! ==============================================================

        #print(f"{self.socket_name}: "
        #      f"put lock ntc_mutex {self.ntc_mutex.get_value()}")
        self.last_used_time = time.time()
        self.ntc_mutex.lock(timeout or -1)

        self.mapfile[0:int_struct.size] = int_struct.pack(len(data))
        self.mapfile[int_struct.size:int_struct.size+len(data)] = data

        # Let the data be read, signalling
        # data is "ready to collect"
        #print(f"{self.socket_name}: "
        #      f"put unlock rtc_mutex {self.rtc_mutex.get_value()}")
        self.rtc_mutex.unlock()

    def get(self, timeout=3):
        """
        Get/pop an item from the (single-item) queue
        :return: the item from the queue
        """
        #print(f"{self.socket_name}: "
        #      f"get lock rtc_mutex {self.rtc_mutex.get_value()}")
        self.last_used_time = time.time()
        self.rtc_mutex.lock(timeout or -1)

        amount = int_struct.unpack(self.mapfile[0:int_struct.size])[0]
        data = self.mapfile[int_struct.size:int_struct.size+amount]

        # Signal there's "nothing to collect"
        # to allow future put operations
        #print(f"{self.socket_name}: "
        #      f"get unlock ntc_mutex {self.ntc_mutex.get_value()}")
        self.ntc_mutex.unlock()
        return data
