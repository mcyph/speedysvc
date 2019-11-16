import msgpack

class MsgPack:
    @staticmethod
    def dumps(o):
        return msgpack.packb(o, encoding='utf-8')

    @staticmethod
    def loads(o):
        return msgpack.unpackb(o, encoding='utf-8')
