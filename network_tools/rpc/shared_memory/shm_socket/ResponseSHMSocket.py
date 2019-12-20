import time
from struct import Struct
from network_tools.rpc.shared_memory.shm_socket.SHMSocketBase import \
    SHMSocketBase
from network_tools.rpc.shared_memory.shared_params import MSG_SIZE
from hybrid_lock import HybridSpinSemaphore, CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE


"""
1: The echoed random short:
   must match the value sent by the client.
2: Response length:
   - Negative values for failure;
   - Positive/0 for success
"""
from_server_encoder = Struct('!Hi')


class ResponseSHMSocket(SHMSocketBase):
    def __init__(self, socket_name, init_resources=False,
                       msg_size=MSG_SIZE):

        SHMSocketBase.__init__(
            self, socket_name, init_resources, msg_size
        )
        mode = (
            CONNECT_TO_EXISTING
            if not init_resources
            else CREATE_NEW_OVERWRITE
        )
        self.put_lock = HybridSpinSemaphore(
            b'response_send_lock_%s' % socket_name.encode('ascii'), mode,
            initial_value=1
        )
        self.recv_lock = HybridSpinSemaphore(
            b'response_recv_lock_%s' % socket_name.encode('ascii'), mode,
            initial_value=1
        )

    def put(self, echo_me, response_data, timeout=-1):
        # It might be this additional "put" lock isn't necessary,
        # as there are locks on the client side
        self.put_lock.lock(timeout or -1)
        try:
            return self.__put(echo_me, response_data)
        finally:
            self.put_lock.unlock()

    def __put(self, echo_me, response_data):
        """
        Send the RPC call response from
        the server to the client.
        """
        PART_SIZE = len(self.mapfile)-from_server_encoder.size
        response_len = len(response_data)

        # The response_len-1 is so that a socket which can send
        # 10 bytes doesn't try to get from the server more than
        # once if there's exactly 10 bytes to receive.
        num_parts = self.get_num_parts(PART_SIZE, response_len)

        for part_num in range(num_parts):
            send_me = (
                from_server_encoder.pack(
                    echo_me, response_len
                ) + response_data[
                    part_num*PART_SIZE:
                    (part_num*PART_SIZE)+PART_SIZE
                ]
            )
            #print(f"extra_parts: {extra_parts}; "
            #      f"response_len: {response_len}; "
            #      f"PART_SIZE: {PART_SIZE}; "
            #      f"part_num: {part_num}; ",
            #      part_num * PART_SIZE,
            #      (part_num * PART_SIZE) + PART_SIZE
            #)
            self.last_used_time = time.time()
            self.ntc_mutex.lock()

            try:
                self.mapfile[0:len(send_me)] = send_me
            except:
                self.ntc_mutex.unlock()
                raise

            self.rtc_mutex.unlock()

            echo_me += 1
            echo_me %= 0b11111111  # Must match value in RequestSHMSocket

    def get(self, expected_echo_data, timeout=-1, spin=1):
        self.recv_lock.lock(timeout or -1)
        try:
            return self.__get(expected_echo_data, timeout or -1, spin)
        finally:
            self.recv_lock.unlock()

    def __get(self, expected_echo_data, timeout=-1, spin=1, multi_parts=True, max_len=None):
        """
        Decode the RPC call response
        on the client side.
        """
        self.last_used_time = time.time()
        self.rtc_mutex.lock(timeout, spin) # We won't make this used in recursive calls, to make sure the entire of the request is receieved

        try:
            echo_me, response_len = \
                from_server_encoder.unpack(
                    self.mapfile[:from_server_encoder.size]
                )
            PART_SIZE = len(self.mapfile)-from_server_encoder.size
            max_len = response_len if max_len is None else max_len
            num_parts = self.get_num_parts(PART_SIZE, response_len)

            data = self.mapfile[
                from_server_encoder.size:
                from_server_encoder.size+min(max_len, response_len)
            ]
            assert expected_echo_data == echo_me, \
                (expected_echo_data, echo_me, data)
        except:
            self.rtc_mutex.unlock()
            raise

        self.ntc_mutex.unlock()

        if multi_parts:
            for x in range(num_parts-1):
                # There should be something on the receiving end!
                #assert not self.recv_lock.get_value()

                expected_echo_data += 1
                expected_echo_data %= 0b11111111  # Must match value in RequestSHMSocket

                data += self.__get(
                    expected_echo_data,
                    timeout=-1,
                    spin=1,
                    multi_parts=False,
                    max_len=response_len-len(data)
                )

        return data
