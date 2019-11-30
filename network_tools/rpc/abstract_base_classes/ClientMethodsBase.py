import inspect
from abc import ABC, abstractmethod
from network_tools.serialisation.RawSerialisation import \
    RawSerialisation


def rpc_call(fn):
    """
    Decorator, signifying the rpc call has
    a corresponding server function
    """
    fn.is_rpc_call = True
    return fn


def from_server_fn(server_fn):
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
                            f"{ len(base_args_no_self) } "
                            f"arguments but "
                            f"{ len(args) + len(kw) } were given"
                        )
                    LArgs.append(argspec.defaults[y])

            return self.send(server_fn, LArgs)
    return fn


class ClientMethodsBase(ABC):
    def __init__(self, client_provider):
        """
        TODO!!!! =====================================================

        :param server_methods:
        """
        #assert isinstance(server_methods, ServerMethodsBase)
        self.server_methods = client_provider.get_server_methods()
        self.client_provider = client_provider

        if self.server_methods is not None:
            self.__verify_methods_exist()

    def __verify_methods_exist(self):
        # Get all client RPC call methods
        LClientMethods = []
        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr):
                LClientMethods.append(name)

        # Make sure all possible methods in server exist in client
        for name in dir(self.server_methods):
            attr = getattr(self.server_methods, name)

            if (
                hasattr(attr, 'serialiser') and
                not name in LClientMethods
            ):
                raise NotImplementedError(
                    f"Method {name} does not exist on client, "
                    f"despite being required by server"
                )

    def send(self, cmd, data):
        """
        Send the command `cmd` to the RPC server.
        Encodes data with the relevant serialiser.
        (JSON/raw bytes etc), before decoding the
        data with the same serialiser.

        :param cmd: the name of the RPC method,
                    as ascii characters
        :param data: the parameters of the RPC
                     method to send to the server
        :return: depends on what the RPC returns - could
                 be almost anything that's encodable
        """
        return self.client_provider.send(cmd, data)
