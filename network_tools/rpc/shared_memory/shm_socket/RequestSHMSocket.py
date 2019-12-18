import time
from struct import Struct
from random import getrandbits
from network_tools.rpc.shared_memory.shm_socket.SHMSocketBase import \
    SHMSocketBase
from network_tools.rpc.shared_memory.shared_params import MSG_SIZE


"""
1: A random short: to make sure response always
   matches command.
   Should never happen - just a regression test,
   so only accepts values from 0-255.
2: Command length (limit 256 chars for a command)
3: Argument length:
   - Negative values for failure;
   - Positive/0 for success
4: The ID of the socket to send the response to.
"""
to_server_encoder = Struct('!HHII')


class RequestSHMSocket(SHMSocketBase):
    def __init__(self, socket_name, init_resources=False,
                       msg_size=MSG_SIZE):

        SHMSocketBase.__init__(
            self,
            socket_name, init_resources,
            msg_size
        )

    def put(self, cmd, args, send_to_client_id, timeout=-1):
        """
        Used on the client side to send
        the parameters to the server
        """

        # Get the data to send
        echo_me = getrandbits(8)
        #print(echo_me, len(cmd), len(args), send_to_client_id)

        part_size = len(self.mapfile) - to_server_encoder.size - len(cmd)
        args_len = len(args)
        num_parts = self.get_num_parts(part_size, args_len)

        for x in range(num_parts):
            send_me = (
                to_server_encoder.pack(
                    echo_me,
                    len(cmd),
                    len(args),
                    send_to_client_id
                ) +
                cmd +
                args[x*part_size:(x*part_size)+part_size]
            )

            # Acquire locks, then send the data
            self.last_used_time = time.time()
            self.ntc_mutex.lock(timeout or -1)
            self.mapfile[0:len(send_me)] = send_me
            self.rtc_mutex.unlock()
        return echo_me

    def get(self, timeout=-1, multi_parts=True, max_len=None):
        """
        Used on the server side to get
        the parameters from the client
        """
        self.last_used_time = time.time()
        self.rtc_mutex.lock(timeout or -1)

        echo_me, cmd_len, args_len, send_to_client_id = \
            to_server_encoder.unpack(
                self.mapfile[:to_server_encoder.size]
            )
        max_len = args_len if max_len is None else max_len

        cmd = self.mapfile[
            to_server_encoder.size:
            to_server_encoder.size+cmd_len
        ]
        args = self.mapfile[
            to_server_encoder.size+cmd_len:
            to_server_encoder.size+cmd_len+min(max_len, args_len)
        ]
        self.ntc_mutex.unlock()

        part_size = len(self.mapfile) - to_server_encoder.size - len(cmd)
        num_parts = self.get_num_parts(part_size, args_len)

        if multi_parts:
            #print(args)
            for x in range(num_parts-1):
                args += self.get(
                    timeout=timeout, # TODO: Should this decrement?? ===================================
                    multi_parts=False,
                    max_len=args_len-len(args)
                )[2]
        #else:
            #print(args)

        return echo_me, cmd, args, send_to_client_id
