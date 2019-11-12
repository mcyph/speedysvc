import msgpack
from cinda.ipc.queue import BaseQueue, SerializedQueue

Q_LEN = 1
MSG_SIZE = 64*1024  # 64kb

MODE_SEND = 0
MODE_RECV = 1


class MessagePackQueue(BaseQueue, SerializedQueue):
    _CODEC = msgpack

    def __init__(self, name, q_len, msg_size):
        #assert mode in (MODE_SEND, MODE_RECV)
        #if mode == MODE_SEND: free(name)
        BaseQueue.__init__(self, name, q_len, msg_size)
