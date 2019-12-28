import inspect
from .serialisation.JSONSerialisation import JSONSerialisation
from .serialisation.MsgPackSerialisation import MsgPackSerialisation
from .serialisation.PickleSerialisation import PickleSerialisation
from .serialisation.RawSerialisation import RawSerialisation
from .serialisation.MarshalSerialisation import MarshalSerialisation
#from .serialisation.ArrowSerialisation import ArrowSerialisation


def __from_server_method(server_fn):
    """
    A lot of methods are identical from client/
    server and shouldn't require extra coding.

    :param server_fn:
    :return:
    """

    # OPEN ISSUE: Should docstrings be copied??? =================================================================

    argspec = inspect.getfullargspec(server_fn)
    base_args_no_self = [
        i for i in argspec.args if i != 'self'
    ]
    default_args_offset = (
        len(base_args_no_self) -
        len(argspec.defaults or ())
    )

    assert not argspec.kwonlyargs, \
        "Server function cannot have any keyword only arguments"
    assert not argspec.kwonlydefaults, \
        "Server function cannot have any keyword only defaults"

    def fn(self, *args, **kw):
        if not kw:
            return self.send(server_fn, args)
        else:
            for k in kw:
                if k not in base_args_no_self:
                    raise TypeError(
                        f"Keyword argument {k} given, "
                        f"but that wasn't an argument in "
                        f"the original server's method"
                    )

            # Fill in server default arguments
            # (if there are any)
            LArgs = []
            LArgs.extend(args)

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
    fn.as_rpc = lambda: __from_server_method(fn)
    return fn


def raw_method(fn):
    """
    Define a method which sends/receives data
    using the python raw `bytes` type
    """
    return __network_method(fn, RawSerialisation)


def json_method(fn):
    """
    Define a method sends/receives data using
    the built-in json module. Tested the most, and quite
    interoperable: I generally use this, unless there's a
    good reason not to.
    """
    return __network_method(fn, JSONSerialisation)


def msgpack_method(fn):
    """
    Define a method that sends/receives data using the
    msgpack module. Supports most/all the types supported
    by json, but typically is 2x+ faster, at the expense
    of (potentially) losing interoperability.
    """
    # OPEN ISSUE: Return json always here, if in REST mode??
    return __network_method(fn, MsgPackSerialisation)


def pickle_method(fn):
    """
    Define a method that sends/receives data using the
    `pickle` module. **Potentially insecure** as arbitrary
    code could be sent, but is very fast, and supports many
    python types. Supports int/tuple etc keys in dicts,
    which json/msgpack don't.
    """
    return __network_method(fn, PickleSerialisation)


def marshal_method(fn):
    """
    Define a method that sends/receives data using the
    `pickle` module. **Potentially insecure** as there
    could be potential buffer overrun vulnerabilities,
    but is very fast.
    """
    return __network_method(fn, MarshalSerialisation)


#def arrow_method(fn):
#    """
#    Define a method that sends/receives data using the
#    `pyarrow` module. Reported to be very fast for numpy
#    `ndarray` types, and support for many of the types that
#    json does, but seemed to be orders of magnitude slower
#    for many other datatypes when I tested it.
#    """
#    return __network_method(fn, ArrowSerialisation)

