class ClientMethodsBase:
    def __init__(self, client_provider):
        """
        TODO!!!! =====================================================

        :param server_methods:
        """
        self.client_provider = client_provider

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
