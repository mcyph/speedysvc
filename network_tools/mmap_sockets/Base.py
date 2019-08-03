import mmap
import struct

from ctypes import c_ushort, c_uint

from dataclasses import dataclass

@dataclass
class MMapVariables:
    cur_state_int: type(c_ushort)
    amount_int: type(c_uint)
    DATA_OFFSET: int


class Base:
    # mmap path for transfers
    PATH = '/tmp/mmapsrv-%s-%s'

    INITIAL_MMAP_FILE_SIZE = 10485760  # 10MB
    INITIAL_MMAP_FILE_SIZE -= INITIAL_MMAP_FILE_SIZE % mmap.PAGESIZE

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

    def get_variables(self, buf):
        cur_state_int = (
            c_ushort.from_buffer(buf)
        )

        AMOUNT_OFFSET = (
            struct.calcsize('@'+cur_state_int._type_)
        )
        amount_int = c_uint.from_buffer(buf, AMOUNT_OFFSET)

        DATA_OFFSET = AMOUNT_OFFSET + struct.calcsize(
            '@'+amount_int._type_
        )

        return MMapVariables(
            cur_state_int, amount_int, DATA_OFFSET
        )