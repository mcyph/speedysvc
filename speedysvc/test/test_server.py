from speedysvc.client_server.base_classes.ServerMethodsBase import \
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
