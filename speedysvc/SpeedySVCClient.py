from typing import Optional, Tuple, Dict, Union, List

from speedysvc.client_server.connect import connect
from speedysvc.compression.compression_types import snappy_compression


class _RemoteIterator:
    def __init__(self, client_inst, return_serialiser, decode_returns, iterator_id):
        self.client_inst = client_inst
        self.return_serialiser = return_serialiser
        self.decode_returns = decode_returns
        self.iterator_id = iterator_id
        self.destroyed = False

    def __del__(self):
        if self.destroyed:
            return
        self.client_inst.send(cmd=b'$iter_destroy$',
                              data=str(self.iterator_id).encode('ascii'))

    def __iter__(self):
        decode_returns = self.decode_returns

        while True:
            data = self.client_inst.send(cmd=b'$iter_next$',
                                         data=str(self.iterator_id).encode('ascii'))
            data = self.return_serialiser.loads(data)
            if not data:
                # Reached the end of the iterator
                # TODO: Indicate this in the last item?
                self.destroyed = True
                break

            for i in data:
                if decode_returns:
                    i = decode_returns(i)
                yield i


class SpeedySVCClient:
    def __init__(self,
                 address: Union[List, Tuple, str],
                 use_spinlock: bool = True,
                 use_in_process_lock: bool = True,
                 compression_inst=snappy_compression):

        self.__address = address
        self.__use_spinlock = use_spinlock
        self.__client_inst = connect(address=address,
                                     use_spinlock=use_spinlock,
                                     use_in_process_lock=use_in_process_lock,
                                     compression_inst=compression_inst)

    def _call_remote_raw(self,
                         metadata,
                         method_name: bytes,
                         data: bytes):
        r = self.__client_inst.send(cmd=method_name,
                                    data=metadata.params_serialiser.dumps(data))
        r = metadata.return_serialiser.loads(r)
        if metadata.decode_returns:
            r = metadata.decode_returns(r)
        return r

    def _iter_remote_raw(self,
                         metadata,
                         method_name: bytes,
                         data: bytes):
        iterator_id = self.__client_inst.send(cmd=method_name,
                                              data=metadata.params_serialiser.dumps(data))
        iterator_id = int(iterator_id)
        return _RemoteIterator(client_inst=self.__client_inst,
                               return_serialiser=metadata.return_serialiser,
                               decode_returns=metadata.decode_returns,
                               iterator_id=iterator_id)  # FIXME: Apply return decoder!!

    def _call_remote(self,
                     metadata,
                     method_name: bytes,
                     positional: Tuple,
                     var_positional: Optional[Tuple],
                     var_keyword: Optional[Dict]):
        r = self.__client_inst.send(cmd=method_name,
                                    data=metadata.params_serialiser.dumps([
                                        positional+var_positional if var_positional else positional,
                                        var_keyword
                                    ]))
        r = metadata.return_serialiser.loads(r)
        if metadata.decode_returns:
            r = metadata.decode_returns(r)
        return r

    def _iter_remote(self,
                     metadata,
                     method_name: bytes,
                     positional: Tuple,
                     var_positional: Optional[Tuple],
                     var_keyword: Optional[Dict]):
        iterator_id = self.__client_inst.send(cmd=method_name,
                                              data=metadata.params_serialiser.dumps([
                                                  positional + var_positional if var_positional else positional,
                                                  var_keyword
                                              ]))
        iterator_id = int(iterator_id)
        return _RemoteIterator(client_inst=self.__client_inst,
                               return_serialiser=metadata.return_serialiser,
                               decode_returns=metadata.decode_returns,
                               iterator_id=iterator_id)
