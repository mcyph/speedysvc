import struct

from ctypes import c_ushort, c_uint


class Base:
    # mmap path for transfers
    PATH = '/tmp/mmaptest-%s'


    # Number of threads on a server, and how
    # many clients can connect at once
    MAX_CONNECTIONS = 25


    # time.sleep performance-related options
    SLEEP_EVERY = 1000
    SLEEP_DIV_BY = 10


    # Current network state
    STATE_DATA_TO_CLIENT = 0
    STATE_CMD_TO_SERVER = 1


    SClientValues = {
        STATE_DATA_TO_CLIENT
    }


    # Remote commands
    CMD_GET = 0
    CMD_PUT = 1
    CMD_ITER_STARTSWITH = 2



    def __init__(self, buf):
        cur_state_int = self.cur_state_int = (
            c_ushort.from_buffer(buf)
        )
        AMOUNT_OFFSET = self.AMOUNT_OFFSET = (
            struct.calcsize('@'+cur_state_int._type_)
        )

        amount_int = self.amount_int = c_uint.from_buffer(buf, AMOUNT_OFFSET)
        self.DATA_OFFSET = AMOUNT_OFFSET + struct.calcsize(
            '@'+amount_int._type_
        )


