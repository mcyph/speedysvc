import time
import _thread
import random
from shmrpc.rpc.base_classes.ClientMethodsBase import ClientMethodsBase
from shmrpc.service_managers.multi_process_manager.test_server import \
    TestServerMethods as srv


class TestClientMethods(ClientMethodsBase):
    def __init__(self, client_provider):
        ClientMethodsBase.__init__(self, client_provider)

    cpu_intensive_method = srv.cpu_intensive_method.as_rpc()


if __name__ == '__main__':
    from shmrpc.rpc.network.NetworkClient import NetworkClient
    from shmrpc.rpc.shared_memory.SHMClient import SHMClient
    from _thread import start_new_thread

    def fn():
        client1 = TestClientMethods(SHMClient(srv))
        client2 = TestClientMethods(SHMClient(srv))

        def fn2():
            while 1:
                r = random.randint(0, 999999999)
                assert client1.cpu_intensive_method(r) == r, r
                r = random.randint(0, 999999999)
                assert client2.cpu_intensive_method(r) == r, r

        for x in range(10):
            _thread.start_new_thread(fn2, ())
        fn2()


    for x in range(10):
        start_new_thread(fn, ())

    while 1:
        time.sleep(10)

