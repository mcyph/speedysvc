import inspect
from .serialisation.JSONSerialisation import JSONSerialisation
from .serialisation.MsgPackSerialisation import MsgPackSerialisation
from .serialisation.PickleSerialisation import PickleSerialisation
from .serialisation.RawSerialisation import RawSerialisation


def from_server_method(server_fn):
    """
    A lot of methods are identical from client/
    server and shouldn't require extra coding.

    :param server_fn:
    :return:
    """
    argspec = inspect.getfullargspec(server_fn)
    base_args_no_self = [
        i for i in argspec.args if i != 'self'
    ]

    assert not argspec.kwonlyargs, \
        "Server function cannot have any keyword only arguments"
    assert not argspec.kwonlydefaults, \
        "Server function cannot have any keyword only defaults"

    def fn(self, *args, **kw):
        if not kw and not argspec.defaults:
            return self.send(server_fn, args)
        else:
            for k in kw:
                if not k in base_args_no_self:
                    raise TypeError(
                        f"Keyword argument {k} given, "
                        f"but that wasn't an argument in "
                        f"the original server's method"
                    )

            # Fill in server default arguments
            # (if there are any)
            LArgs = []
            LArgs.extend(args)
            default_args_offset = (
                len(base_args_no_self) -
                len(argspec.defaults)
            )

            for x in range(len(args), len(base_args_no_self)):
                if base_args_no_self[x] in kw:
                    LArgs.append(kw[base_args_no_self[x]])
                else:
                    y = x - default_args_offset
                    if y < 0:
                        raise TypeError(
                            f"{ server_fn.__name__ } takes "
                            f"{ len(base_args_no_self) } arguments but "
                            f"{ len(args) + len(kw) } were given"
                        )
                    LArgs.append(argspec.defaults[y])

            return self.send(server_fn, LArgs)
    return fn


def __network_method(fn, serialiser):
    """

    :param fn:
    :param serialiser:
    :return:
    """
    assert not hasattr(fn, 'serialiser'), \
        f"Serialiser has already been set for {fn}"
    fn.serialiser = serialiser
    fn.as_rpc = lambda: from_server_method(fn)
    return fn


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
