from network_tools.rpc.base_classes.ClientMethodsBase import \
    ClientMethodsBase
from network_tools.rpc.network.test_server import \
    TestServerMethods as srv


class TestClientMethods(ClientMethodsBase):
    def __init__(self, client_provider):
        ClientMethodsBase.__init__(self, client_provider)

    test_defaults = srv.test_defaults.as_rpc()
    test_json_echo = srv.test_json_echo.as_rpc()
    test_raw_echo = srv.test_raw_echo.as_rpc()
    test_pickle_echo = srv.test_pickle_echo.as_rpc()
    test_marshal_echo = srv.test_marshal_echo.as_rpc()
    test_msgpack_method = srv.test_msgpack_method.as_rpc()
    test_arrow_method = srv.test_arrow_method.as_rpc()


NUM_ITERATIONS = 100000
SERIALISE_ME = {
    'a': [1, 2, 3, 'b', 5.0],
    'dsadsadasdas': 'gfhsdjkfdshjkf'
}
#SERIALISE_ME = (1, 2, 3)
import numpy



if __name__ == '__main__':
    from network_tools.rpc.network.NetworkClient import \
        NetworkClient
    from network_tools.rpc.shared_memory.SHMClient import SHMClient
    from time import time

    client = TestClientMethods(NetworkClient(srv))

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_defaults(SERIALISE_ME)
    print("args1:", time() - t_from)

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_defaults(SERIALISE_ME, default="blah2")
    print("args2:", time() - t_from)

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_defaults(SERIALISE_ME, "blah2")
    #client.test_defaults("blah", default2="blah2")
    print("args3:", time() - t_from)

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_json_echo(SERIALISE_ME)
    print("json:", time() - t_from)

    t_from = time()
    raw_data = repr(SERIALISE_ME).encode('utf-8')
    for x in range(NUM_ITERATIONS):
        client.test_raw_echo(raw_data)
    print("raw (not comparable)", time() - t_from)

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_pickle_echo(SERIALISE_ME)
    print("pickle:", time() - t_from)

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_marshal_echo(SERIALISE_ME)
    print("marshal:", time() - t_from)

    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_msgpack_method(SERIALISE_ME)
    print("msgpack:", time() - t_from)

    SERIALISE_ME = numpy.ndarray(SERIALISE_ME)
    t_from = time()
    for x in range(NUM_ITERATIONS):
        client.test_arrow_method(SERIALISE_ME)
    print("arrow:", time() - t_from)
