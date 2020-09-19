import timeit
import multiprocessing

from speedysvc.client_server.base_classes.ClientMethodsBase import ClientMethodsBase
from speedysvc.test.test_server import TestServerMethods as srv
from speedysvc.client_server.network.NetworkClient import NetworkClient
from speedysvc.client_server.shared_memory.SHMClient import SHMClient
from speedysvc.client_server.connect import connect


class TestClientMethods(ClientMethodsBase):
    def __init__(self, client_provider):
        ClientMethodsBase.__init__(self, client_provider)

    test_defaults = srv.test_defaults.as_rpc()
    test_json_echo = srv.test_json_echo.as_rpc()
    test_raw_echo = srv.test_raw_echo.as_rpc()
    test_raw_return_len = srv.test_raw_return_len.as_rpc()
    test_pickle_echo = srv.test_pickle_echo.as_rpc()
    test_marshal_echo = srv.test_marshal_echo.as_rpc()
    test_msgpack_method = srv.test_msgpack_method.as_rpc()


NUM_ITERATIONS = 100000
SERIALISE_ME = {
    'a': [1, 2, 3, 'b', 5.0],
    'dsadsadasdas': 'gfhsdjkfdshjkf'
}
#SERIALISE_ME = (1, 2, 3)
import numpy


MSG_SIZE = 5000 # HACK!


def run_test():
    client = TestClientMethods(
        connect(srv, address=(
           #'tcp://192.168.0.44', # Shouldn't work
           #'tcp://127.0.0.1',
           'shm://',
        )
    ))

    LClients = []
    #for x in range(10):
    #    LClients.append(TestClientMethods(SHMClient(srv)))
    raw_data = repr(SERIALISE_ME).encode('utf-8')
    for x in range(MSG_SIZE-20, MSG_SIZE+20):
        print(x)
        assert client.test_raw_return_len(str(x).encode('ascii')) == b'Z'*x, x

    """
    print("RUNNING LEN TESTS!")
    import random
    R = str(random.random()).encode('ascii') * 100000
    for x in range(len(R)): # MSG_SIZE*3
        i = R[:x]
        assert i == client.test_raw_echo(i)
        for c in LClients:
            assert i == c.test_raw_echo(i)

        #print(i==client.test_raw_echo(i))
        #print(i, client.test_raw_echo(i))
    #print(len(R), len(client.test_raw_echo(R)), R==client.test_raw_echo(R))
    #raise SystemExit
    """

    for text, stmt in (
        ("args1:", "client.test_defaults(SERIALISE_ME)"),
        ("args2:", "client.test_defaults(SERIALISE_ME, default='blah2')"),
        ("args3:", 'client.test_defaults(SERIALISE_ME, "blah2")'),
        ("json:", "client.test_json_echo(SERIALISE_ME)"),
        ("raw (not comparable):", "client.test_raw_echo(raw_data)"),
        ("pickle:", "client.test_pickle_echo(SERIALISE_ME)"),
        ("marshal:", "client.test_marshal_echo(SERIALISE_ME)"),
        ("msgpack:", "client.test_msgpack_method(SERIALISE_ME)"),
        #("arrow:", "client.test_arrow_method(SERIALISE_ME)"),
    ):
        print(text, timeit.timeit(
            stmt,
            setup='client=_client; '
                  'SERIALISE_ME=_SERIALISE_ME; '
                  'raw_data=_raw_data',
            globals={
                '_client': client,
                '_SERIALISE_ME': SERIALISE_ME,
                '_raw_data': raw_data
            },
            number=NUM_ITERATIONS
        ))

    import time
    while True:
        time.sleep(1)


if __name__ == '__main__':
    for x in range(1):
        p = multiprocessing.Process(target=run_test)
        p.start()

    import time
    while True:
        time.sleep(1)
