import pickle


class PickleSerialisation:
    """
    A serialiser that uses python pickle.

    This has the advantage that it may be fast,
    and sometimes support serialisation of
    e.g. custom classes or tuples/int's as dict keys,
    it may introduce security issues and reduce
    interopability with other languages than python,
    so I generally don't use this.
    """
    name = 'pickle'
    mimetype = 'application/octet-stream'

    @staticmethod
    def dumps(o):
        return pickle.dumps(o)

    @staticmethod
    def loads(o):
        return pickle.loads(o)
