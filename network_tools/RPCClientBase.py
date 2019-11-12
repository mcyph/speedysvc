from abc import ABC, abstractmethod


class RPCClientBase:
    @abstractmethod
    def send_json(self):
        pass

    @abstractmethod
    def send_msgpack(self):
        pass

    @abstractmethod
    def send_bytes(self):
        pass

