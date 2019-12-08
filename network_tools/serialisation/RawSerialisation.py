class RawSerialisation:
    """
    A "serialiser" that just does nothing,
    only returning raw `bytes`
    (and making sure that bytes is indeed
    the type that is being sent/received).
    """
    mimetype = 'application/octet-stream'

    @staticmethod
    def dumps(o):
        if isinstance(o, (list, tuple)):
            assert len(o) == 1, \
                f"{o} can only be a list/tuple of " \
                f"len 1 with a bytes object in it"
            o = o[0]

        if not isinstance(o, bytes):
            raise TypeError(f"Object {o} should be of type bytes")
        return o

    @staticmethod
    def loads(o):
        if not isinstance(o, bytes):
            raise TypeError(f"Object {o} should be of type bytes")
        return o
