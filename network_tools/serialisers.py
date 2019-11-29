from .serialisation.JSONSerialisation import JSONSerialisation
from .serialisation.MsgPackSerialisation import MsgPackSerialisation
from .serialisation.PickleSerialisation import PickleSerialisation
from .serialisation.RawSerialisation import RawSerialisation


def __network_method(fn, serialiser):
    """

    :param fn:
    :param serialiser:
    :return:
    """
    assert not hasattr(fn, 'serialiser'), \
        f"Serialiser has already been set for {fn}"

    def new_fn(*args):
        args = serialiser.loads(args)
        r = fn(*args)
        return serialiser.dumps(r)
    return new_fn


def raw_method(fn):
    """

    :param fn:
    :return:
    """
    return __network_method(fn, RawSerialisation)


def json_method(fn):
    """

    :param fn:
    :return:
    """
    return __network_method(fn, JSONSerialisation)


def msgpack_method(fn):
    """

    :param fn:
    :return:
    """
    return __network_method(fn, MsgPackSerialisation)


def pickle_method(fn):
    """

    :param fn:
    :return:
    """
    return __network_method(fn, PickleSerialisation)

