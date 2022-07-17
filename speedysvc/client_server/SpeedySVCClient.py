from typing import Optional, Tuple, Dict

from speedysvc.client_server.connect import connect


class _RemoteIterator:
    def __init__(self, client_inst, from_method, iterator_id):
        self.client_inst = client_inst
        self.from_method = from_method
        self.iterator_id = iterator_id
        self.destroyed = False

    def __del__(self):
        self.client_inst.send(cmd='$iter_destroy$',
                              args=str(self.iterator_id).encode('ascii'),
                              timeout=-1)

    def __iter__(self):
        while True:
            data = self.client_inst.send(cmd='$iter_next$',
                                         args=str(self.iterator_id).encode('ascii'),
                                         timeout=-1)
            data = self.from_method.return_serialiser.deserialise(data)
            if not data:
                # Reached the end of the iterator
                # TODO: Indicate this in the last item?
                self.destroyed = True
                break

            for i in data:
                yield i


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
                                    args=from_method.params_serialiser.dumps(data),
                                    timeout=-1)
        return from_method.return_serialiser.deserialise(r)

    def _iter_remote_raw(self,
                         from_method,
                         method_name: str,
                         data: bytes):
        iterator_id = self.__client_inst.send(cmd=method_name,
                                              args=from_method.params_serialiser.dumps(data),
                                              timeout=-1)
        iterator_id = int(iterator_id)
        return _RemoteIterator(self.__client_inst, from_method, iterator_id)

    def _call_remote(self,
                     from_method,
                     method_name: str,
                     positional: Tuple,
                     var_positional: Optional[Tuple],
                     var_keyword: Optional[Dict]):
        r = self.__client_inst.send(cmd=method_name,
                                    args=from_method.params_serialiser.dumps([
                                        positional+var_positional if var_positional else positional,
                                        var_keyword
                                    ]),
                                    timeout=-1)
        return from_method.return_serialiser.deserialise(r)

    def _iter_remote(self,
                     from_method,
                     method_name: str,
                     positional: Tuple,
                     var_positional: Optional[Tuple],
                     var_keyword: Optional[Dict]):
        iterator_id = self.__client_inst.send(cmd=method_name,
                                              args=from_method.params_serialiser.dumps([
                                                  positional + var_positional if var_positional else positional,
                                                  var_keyword
                                              ]),
                                              timeout=-1)
        iterator_id = int(iterator_id)
        return _RemoteIterator(self.__client_inst, from_method, iterator_id)