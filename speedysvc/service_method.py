from .serialisation.serialisation_types import get_by_name


def service_method(params='json',
                   returns='json'):
    """
    Define a method which will be serialised using JSON types with
    a suitable encoder (e.g. the json module, msgpack, bson etc).
    """
    def return_fn(fn):
        return __network_method(fn, get_by_name(params), get_by_name(returns))
    return return_fn


def __network_method(fn,
                     params_serialiser,
                     return_serialiser):
    assert not hasattr(fn, 'serialiser'), \
        f"Serialiser has already been set for {fn}"
    fn.params_serialiser = params_serialiser
    fn.return_serialiser = return_serialiser
    fn.metadata = {
        'num_calls': 0,
        'total_time': 0
    }
    return fn

