import pyarrow



class ArrowSerialisation:
    """
    TODO!
    """

    mimetype = 'application/octet-stream'

    @staticmethod
    def dumps(o):
        return pyarrow.serialize(o).to_buffer()

    @staticmethod
    def loads(o):
        return pyarrow.deserialize(o)
