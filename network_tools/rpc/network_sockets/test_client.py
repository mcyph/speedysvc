from network_tools.rpc.abstract_base_classes.ClientMethodsBase import \
    ClientMethodsBase
from network_tools.rpc.network_sockets.test_server import \
    TestServerMethods as srv


class TestClientMethods(ClientMethodsBase):
    def __init__(self, client_provider):
        ClientMethodsBase.__init__(self, client_provider)

    test_defaults = srv.test_defaults.as_rpc()
    test_json_echo = srv.test_json_echo.as_rpc()
    test_raw_echo = srv.test_raw_echo.as_rpc()
    test_pickle_echo = srv.test_pickle_echo.as_rpc()
    test_msgpack_method = srv.test_msgpack_method.as_rpc()


if __name__ == '__main__':
    from network_tools.rpc.network_sockets.NetworkClient import \
        NetworkClient
    from network_tools.rpc.posix_shm_sockets.SHMClient import SHMClient

    client = TestClientMethods(SHMClient(srv))
    print(client.test_defaults("blah"))
    print(client.test_defaults("blah", default="blah2"))
    print(client.test_defaults("blah", "blah2"))
    #print(client.test_defaults("blah", default2="blah2"))
    print()
    print(client.test_json_echo("blah"))
    print(client.test_raw_echo(b"blah"))
    print(client.test_pickle_echo("blah"))
    print(client.test_msgpack_method("blah"))
