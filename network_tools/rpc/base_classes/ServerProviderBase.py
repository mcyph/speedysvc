from network_tools.serialisation.RawSerialisation import \
    RawSerialisation


class ServerProviderBase:
    ___init = False

    def __call__(self, server_methods):
        """
        TODO!!!! ===========================================================

        :param server_inst:
        """
        # Couldn't see much reason to have an abstract base class here,
        # as the "serve" logic is implementation-specific
        self.server_methods = server_methods
        self.port = server_methods.port
        self.name = server_methods.name

        assert not self.___init, \
            f"{self.__class__} has already been started!"
        self.___init = True

    def handle_fn(self, cmd, args):
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
