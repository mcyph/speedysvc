class MultiProcessServer:
    def __init__(self,
                 server_methods=False,
                 network_server=False,
                 shm_server=True):

        assert network_server or shm_server, \
            "MultiProcessManager should start as either a network or shared memory server!"
