
class ServerProviderBase:
    def __init__(self, server_methods):
        """
        TODO!!!! ===========================================================

        :param server_inst:
        """
        # Couldn't see much reason to have an abstract base class here,
        # as the "serve" logic is implementation-specific
        self.server_methods = server_methods
        self.port = server_methods.port
        self.name = server_methods.name
