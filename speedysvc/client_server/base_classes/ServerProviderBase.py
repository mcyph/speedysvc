from speedysvc.serialisation.RawSerialisation import RawSerialisation


class ServerProviderBase:
    ___init = False

    def __init__(self,
                 server_methods,
                 service_port: int,
                 service_name: str):

        # Couldn't see much reason to have an abstract base class here,
        # as the "serve" logic is implementation-specific
        self.server_methods = server_methods
        self.service_port = service_port
        self.service_name = service_name

        assert not self.___init, \
            f"{self.__class__} has already been started!"
        self.___init = True

    def handle_fn(self,
                  cmd: bytes,
                  args: bytes):

        fn = getattr(self.server_methods, cmd.decode('ascii'))

        # Use the serialiser to decode the arguments,
        # before encoding the return value of the RPC call
        if fn.serialiser == RawSerialisation:
            # Special case: if the data is just raw bytes
            # (not a list of parameters) treat it as just
            # a single parameter
            args = (args,)
        else:
            args = fn.serialiser.loads(args)

        result = fn(*args)
        result = fn.serialiser.dumps(result)
        return result
