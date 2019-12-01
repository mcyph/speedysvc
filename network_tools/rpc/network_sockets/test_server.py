from network_tools.rpc.base_classes.ServerMethodsBase import \
    ServerMethodsBase
from network_tools.rpc_decorators import \
    json_method, raw_method, pickle_method, \
    msgpack_method, marshal_method


class TestServerMethods(ServerMethodsBase):
    port = 5555
    name = 'echo_serv'

    def __init__(self):
        ServerMethodsBase.__init__(self)

    @json_method
    def test_defaults(self, data, default='test'):
        return (data, default)

    @json_method
    def test_json_echo(self, data):
        return data

    @raw_method
    def test_raw_echo(self, data):
        return data

    @pickle_method
    def test_pickle_echo(self, data):
        return data

    @marshal_method
    def test_marshal_echo(self, data):
        return data

    @msgpack_method
    def test_msgpack_method(self, data):
        return data


if __name__ == '__main__':
    from time import sleep
    from network_tools.rpc.network_sockets.NetworkServer import \
        NetworkServer
    from network_tools.rpc.posix_shm_sockets.SHMServer import SHMServer

    provider = SHMServer(TestServerMethods())

    while 1:
        sleep(10)
