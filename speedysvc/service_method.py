from dataclasses import dataclass
from speedysvc.serialisation.serialisation_types import get_by_name


@dataclass
class FunctionMetaData:
    params_serialiser: Any
    return_serialiser: Any

    decode_params: Optional[Dict[str, Callable]] = None
    encode_params: Optional[Dict[str, Callable]] = None
    decode_returns: Optional[Callable] = None
    encode_returns: Optional[Callable] = None

    returns_iterator: bool = False
    iterator_page_size: int = 1000

    num_calls: int = 0
    total_time: int = 0


def service_method(params: str = 'json',
                   returns: str = 'json',
                   decode_params: Optional[Dict[str, Callable]] = None,
                   encode_params: Optional[Dict[str, Callable]] = None,
                   decode_returns: Optional[Callable] = None,
                   encode_returns: Optional[Callable] = None,
                   returns_iterator: bool = False,
                   iterator_page_size: int = 1000):
    """
    Define a method which will be serialised using JSON types with
    a suitable encoder (e.g. the json module, msgpack, bson etc).
    """
    metadata = FunctionMetaData(params_serialiser=get_by_name(params),
                                return_serialiser=get_by_name(returns),
                                decode_params=decode_params,
                                encode_params=encode_params,
                                decode_returns=decode_returns,
                                encode_returns=encode_returns,
                                returns_iterator=returns_iterator,
                                iterator_page_size=iterator_page_size)

    def return_fn(fn):
        assert not hasattr(fn, 'metadata'), f"Metadata has already been set for {fn}"
        fn.metadata = metadata
        return fn

    return return_fn

