import msgpack


class MsgPackSerialisation:
    """
    Very similar to JSONSerialisation in terms of the
    types it supports, but is a binary format and often
    faster.
    """
    mimetype = 'application/msgpack'

    @staticmethod
    def dumps(o):
        return msgpack.packb(o, encoding='utf-8')

    @staticmethod
    def loads(o):
        return msgpack.unpackb(o, encoding='utf-8')
