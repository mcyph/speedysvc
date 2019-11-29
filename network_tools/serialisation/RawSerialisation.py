class RawSerialisation:
    """
    A "serialiser" that just does nothing,
    only returning raw `bytes`
    (and making sure that bytes is indeed
    the type that is being sent/received).
    """

    @staticmethod
    def dumps(o):
        if not isinstance(o, bytes):
            raise TypeError(f"Object {o} should be of type bytes")
        return o

    @staticmethod
    def loads(o):
        if not isinstance(o, bytes):
            raise TypeError(f"Object {o} should be of type bytes")
        return o
