def client_server_fn(fn):
    fn.is_client_server = True
    return fn


RPC_TYPE_MMAP = 0
RPC_TYPE_NETWORK = 1
RPC_TYPE_SSH = 2


class SSHSettings:
    def __init__(self, rpc_type, port, bind_to_ip='localhost'):
        self.rpc_type = rpc_type
        self.port = port
        self.bind_to_ip = bind_to_ip

    def get_private_key(self):
        pass

    def gen_private_key(self):
        pass

    def get_public_key(self):
        pass


class MMapSettings:
    pass


class ClientServerBase:
    """
    TODO: Create a means by which
    """
    def __init__(self, settings_properties):
        self.__settings_properties = settings_properties

    @staticmethod
    def serve_forever(cls, *args, **kw):
        return

    def __new_server_fn(self, old_fn):
        pass


    @staticmethod
    def make_client(cls, *args, **kw):
        if self.__settings_properties == RPC_TYPE_MMAP:
            self.__client = MMapClient(self.__settings_properties)
        elif self.__settings_properties == RPC_TYPE_NETWORK:
            self.__client = NetworkClient(self.__settings_properties)

        for name in dir(self):
            attr = getattr(self, name)

            if hasattr(attr, 'is_client_server') and attr.is_client_server:
                setattr(self, name, self.__new_client_fn(name, attr))

        return self

    def __new_client_fn(self, fn_name, old_fn):
        def new_fn(*args, **kw):
            return self.__client.send(*args, **kw)
        return new_fn


class ClientFactory:
    pass

class ServerFactory:
    pass

