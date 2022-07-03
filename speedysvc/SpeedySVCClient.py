from typing import Optional, Tuple, Dict

from speedysvc.client_server.connect import connect


class SpeedySVCClient:
    def __init__(self,
                 address: Union[List, Tuple, str],
                 use_spinlock=True,
                 use_in_process_lock=True,
                 compression_inst=snappy_compression):

        self.__address = address
        self.__use_spinlock = use_spinlock
        self.__bind_ip = bind_ip
        self.__client_inst = connect(address=address,
                                     use_spinlock=use_spinlock,
                                     use_in_process_lock=use_in_process_lock,
                                     compression_inst=compression_inst)

    def _call_remote_raw(self,
                         from_method,
                         method_name: str,
                         data: bytes):
        r = self.__client_inst.send(cmd=method_name,
                                    args=from_method.params_serialiser.serialise(data),
                                    timeout=-1)
        return from_method.return_serialiser.deserialise(r)

    def _call_remote(self,
                     from_method,
                     method_name: str,
                     positional: Tuple,
                     var_positional: Optional[Tuple],
                     var_keyword: Optional[Dict]):
        r = self.__client_inst.send(cmd=method_name,
                                    args=from_method.params_serialiser.serialise([method_name,
                                                                                  positional,
                                                                                  var_positional,
                                                                                  var_keyword]),
                                    timeout=-1)
        return from_method.return_serialiser.deserialise(r)
