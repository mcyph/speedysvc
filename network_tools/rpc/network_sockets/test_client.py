from network_tools.rpc.abstract_base_classes.ClientMethodsBase import ClientMethodsBase, from_server_fn
from network_tools.rpc.network_sockets.test_server import TestServerMethods as srv


class TestClientMethods(ClientMethodsBase):
    def __init__(self, client_provider):
        ClientMethodsBase.__init__(self, client_provider)

    test_json_echo = from_server_fn(srv.test_json_echo)
    test_raw_echo = from_server_fn(srv.test_raw_echo)
    test_pickle_echo = from_server_fn(srv.test_pickle_echo)
    test_msgpack_method = from_server_fn(srv.test_msgpack_method)

    #def test_json_echo(self, data):
    #    return self.send(srv.test_json_echo, data)

    #def test_raw_echo(self, data):
    #    return self.send(srv.test_raw_echo, data)

    #def test_pickle_echo(self, data):
    #    return self.send(srv.test_pickle_echo, data)

    #def test_msgpack_method(self, data):
    #    return self.send(srv.test_msgpack_method, data)


if __name__ == '__main__':
    from network_tools.rpc.network_sockets.NetworkClient import \
        NetworkClient
    from network_tools.rpc.posix_shm_sockets.SHMClient import SHMClient

    client = TestClientMethods(SHMClient(srv))
    print(client.test_json_echo("blah"))
    print(client.test_raw_echo(b"blah"))
    print(client.test_pickle_echo("blah"))
    print(client.test_msgpack_method("blah"))
