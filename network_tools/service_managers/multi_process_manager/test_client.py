import time
from network_tools.rpc.base_classes.ClientMethodsBase import ClientMethodsBase
from network_tools.service_managers.multi_process_manager.test_server import \
    TestServerMethods as srv


class TestClientMethods(ClientMethodsBase):
    def __init__(self, client_provider):
        ClientMethodsBase.__init__(self, client_provider)

    cpu_intensive_method = srv.cpu_intensive_method.as_rpc()


if __name__ == '__main__':
    from network_tools.rpc.network.NetworkClient import NetworkClient
    from network_tools.rpc.shared_memory.SHMClient import SHMClient
    from _thread import start_new_thread

    def fn():
        client = TestClientMethods(SHMClient(srv))
        while 1:
            client.cpu_intensive_method()


    for x in range(10):
        start_new_thread(fn, ())

    while 1:
        time.sleep(10)

