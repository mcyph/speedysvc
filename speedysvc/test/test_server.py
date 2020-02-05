from speedysvc.rpc.base_classes.ServerMethodsBase import \
    ServerMethodsBase
from speedysvc.rpc_decorators import \
    json_method, raw_method, pickle_method, \
    msgpack_method, marshal_method#, arrow_method


class TestServerMethods(ServerMethodsBase):
    port = 5555
    name = 'echo_serv'

    def __init__(self, logger_client):
        ServerMethodsBase.__init__(self, logger_client)

    @json_method
    def test_defaults(self, data, default='test'):
        return (data, default)

    @json_method
    def test_json_echo(self, data):
        return data

    @raw_method
    def test_raw_echo(self, data):
        #print("RAW DATA LEN:", len(data))
        return data

    @raw_method
    def test_raw_return_len(self, data):
        return b'Z'*int(data)

    @pickle_method
    def test_pickle_echo(self, data):
        return data

    @marshal_method
    def test_marshal_echo(self, data):
        return data

    @msgpack_method
    def test_msgpack_method(self, data):
        return data

    #@arrow_method
    #def test_arrow_method(self, data):
    #    return data


if __name__ == '__main__':
    import multiprocessing
    from time import sleep
    from speedysvc.rpc.network.NetworkServer import \
        NetworkServer
    from speedysvc.rpc.shared_memory.SHMServer import SHMServer

    network_server = NetworkServer(TestServerMethods)

    def run_me(init_resources):
        methods = TestServerMethods()
        provider1 = SHMServer()(methods, init_resources=init_resources)
        provider2 = network_server(methods)
        while 1: sleep(10)

    for x in range(1):
        p = multiprocessing.Process(target=run_me, args=(not x,))
        p.start()
        if not x:
            sleep(2)

    while 1:
        sleep(10)
