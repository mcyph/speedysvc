import time
from struct import Struct
from network_tools.rpc.shared_memory.shm_socket.SHMSocketBase import \
    SHMSocketBase
from network_tools.rpc.shared_memory.shared_params import MSG_SIZE


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
            self,
            socket_name, init_resources,
            msg_size
        )

    def put(self, echo_me, response_data, timeout=-1):
        """
        Send the RPC call response from
        the server to the client.
        """
        PART_SIZE = len(self.mapfile)-from_server_encoder.size
        response_len = len(response_data)

        # The response_len-1 is so that a socket which can send
        # 10 bytes doesn't try to get from the server more than
        # once if there's exactly 10 bytes to receive.
        extra_parts = (response_len-(response_len % PART_SIZE)) // PART_SIZE

        for part_num in range(extra_parts+1):
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
            self.ntc_mutex.lock(timeout or -1)
            self.mapfile[0:len(send_me)] = send_me
            self.rtc_mutex.unlock()

            echo_me += 1
            echo_me %= 0b11111111  # Must match value in RequestSHMSocket

    def get(self, expected_echo_data, timeout=-1, multi_parts=True, max_len=None):
        """
        Decode the RPC call response
        on the client side.
        """
        self.last_used_time = time.time()
        self.rtc_mutex.lock(timeout or -1)

        echo_me, response_len = \
            from_server_encoder.unpack(
                self.mapfile[:from_server_encoder.size]
            )
        PART_SIZE = len(self.mapfile)-from_server_encoder.size
        response_len = response_len or 1
        max_len = response_len if max_len is None else max_len
        extra_parts = (response_len-(response_len % PART_SIZE)) // PART_SIZE

        assert expected_echo_data == echo_me

        data = self.mapfile[
            from_server_encoder.size:
            from_server_encoder.size+min(max_len, response_len)
        ]
        self.ntc_mutex.unlock()

        if multi_parts:
            for x in range(extra_parts):
                expected_echo_data += 1
                expected_echo_data %= 0b11111111  # Must match value in RequestSHMSocket

                data += self.get(
                    expected_echo_data,
                    timeout=timeout, # TODO: Should this decrement?? ===================================
                    multi_parts=False,
                    max_len=response_len-len(data)
                )
        return data
