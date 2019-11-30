class ClientMethodsBase:
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
