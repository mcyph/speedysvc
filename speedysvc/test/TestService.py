from typing import Any

from speedysvc.service_method import service_method
from speedysvc.client_server.base_classes.ServerProviderBase import ServerProviderBase


class TestService:
    def __init__(self, logger_client):
        self.logger_client = logger_client

    @service_method(params='raw',
                    returns='raw')
    def test_raw_return_len(self, data):
        return b'Z' * int(data)

    @service_method()
    def test_defaults(self, data, default='test'):
        return data, default

    @service_method()
    def test_json_echo(self, data):
        return data

    @service_method(returns_iterator=True,
                    iterator_page_size=10000)
    def test_json_echo_iterator(self, data):
        for x in range(1000000):
            yield data

    @service_method(params='raw',
                    returns='raw')
    def test_raw_echo(self, data):
        #print("RAW DATA LEN:", len(data))
        return data

    @service_method(params='raw',
                    returns='raw')
    def test_raw_return_len(self, data):
        return b'Z'*int(data)

    @service_method(params='pickle',
                    returns='pickle')
    def test_pickle_echo(self, data):
        return data

    @service_method(params='marshal',
                    returns='marshal')
    def test_marshal_echo(self, data):
        return data

    @service_method(params='msgpack',
                    returns='msgpack')
    def test_msgpack_method(self, data):
        return data

    #@arrow_method
    #def test_arrow_method(self, data):
    #    return data
