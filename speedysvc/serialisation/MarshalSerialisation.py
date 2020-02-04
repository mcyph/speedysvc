import marshal


class MarshalSerialisation:
    """
    A serialiser that uses python marshal.

    This has the advantage that it may be fast,
    and sometimes support serialisation of
    e.g. tuples/int's as dict keys, but
    it may introduce security issues and reduce
    interopability with other languages than python,
    so I generally don't use this.

    Marshal isn't even guaranteed to be constant
    across releases, though that may be less of an
    issue where python versions are the same.
    """

    mimetype = 'application/octet-stream'

    @staticmethod
    def dumps(o):
        return marshal.dumps(o)

    @staticmethod
    def loads(o):
        return marshal.loads(o)
