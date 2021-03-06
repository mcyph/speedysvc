class ServerMethodsBase:
    def __init__(self, logger_client):
        """
        TODO!!! =========================================================
        """
        assert hasattr(self, 'port')
        assert hasattr(self, 'name')

        self.logger_client = self.log = logger_client

    """
    `port` Must be implemented by classes
    which supply server methods.

    It is the unique numeric port of the server,
    to allow serving on TCP, shared memory
    (and potentially others) seamlessly.
    """

    """
    `name` Must be implemented by classes
    which supply server methods.

    It is the string description of the server,
    preferably short so as to allow putting
    in process names.
    """
