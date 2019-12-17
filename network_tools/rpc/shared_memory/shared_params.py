from math import ceil
from random import getrandbits
from struct import Struct


MSG_SIZE = 1000000 # 1mb 64*1024  # 64kb

MODE_SEND = 0
MODE_RECV = 1


# 1: A random short: to make sure response always
#    matches command.
#    Should never happen - just a regression test,
#    so only accepts values from 0-255.
# 2: Command length (limit 256 chars for a command)
# 3: Argument length:
#    - Negative values for failure;
#    - Positive/0 for success
# 4: The ID of the socket to send the response to.


to_server_encoder = Struct('!HIHI')


class ToServerEncoder:
    @staticmethod
    def encode(cmd, args, send_to_client_id):
        """
        Used on the client side to send
        the parameters to the server
        """
        echo_me = getrandbits(0b11111111)
        return echo_me, to_server_encoder.pack(
            echo_me, len(cmd), len(args), send_to_client_id
        ) + cmd + args

    @staticmethod
    def decode(data):
        """
        Used on the server side to get
        the parameters from the client
        """
        echo_me, cmd_len, arg_len, send_to_client_id = \
            to_server_encoder.unpack(
                data[:to_server_encoder.size]
            )

        cmd = data[
            to_server_encoder.size:
            to_server_encoder.size+cmd_len
        ]
        args = data[
            to_server_encoder.size+cmd_len:
            to_server_encoder.size+cmd_len+arg_len
        ]

        return echo_me, cmd, args, send_to_client_id


# 1: The echoed random short:
#    must match the value sent by the client.
# 2: Response length:
#    - Negative values for failure;
#    - Positive/0 for success


# TODO: Make work with multipart results!!! ================
# It might be possible to simply have the server send
# n parts successively thru the "to client" socket
from_server_encoder = Struct('!Hi')


class FromServerEncoder:
    @staticmethod
    def encode(echo_me, response_data, mmap):
        """
        Send the RPC call response from
        the server to the client.
        """
        L = []
        PART_SIZE = len(mmap)-from_server_encoder.size
        response_len = len(response_data) or 1
        # The response_len-1 is so that a socket which can send
        # 10 bytes doesn't try to get from the server more than
        # once if there's exactly 10 bytes to receive.
        extra_parts = (response_len-1) // PART_SIZE  #FIXME!!

        for part_num in range(extra_parts+1):
            L.append(
                from_server_encoder.pack(
                    echo_me, response_len
                ) + response_data[
                    part_num*PART_SIZE:
                    (part_num*PART_SIZE)+PART_SIZE
                ]
            )
        return L

    @staticmethod
    def decode(expected_echo_data, mmap):
        """
        Decode the RPC call response
        on the client side.
        """
        echo_me, response_len = \
            from_server_encoder.unpack(
                mmap[:from_server_encoder.size]
            )
        PART_SIZE = len(mmap)-from_server_encoder.size
        response_len = response_len or 1
        extra_parts = (response_len-1) // PART_SIZE  #FIXME!!

        assert expected_echo_data == echo_me

        return extra_parts, mmap[
            from_server_encoder.size:
            from_server_encoder.size+response_len
        ]

