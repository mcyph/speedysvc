import multiprocessing
from network_tools.posix_shm_sockets.SHMServer import SHMServer


class SHMMultiServer:
    def __init__(self, client_factory, num_clients):
        self.LProcesses = []

        for x in range(num_clients):
            self.LProcesses.append(
                multiprocessing.Process(target=client_factory)
            )

