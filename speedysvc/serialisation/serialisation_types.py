from speedysvc.serialisation.RawSerialisation import RawSerialisation
from speedysvc.serialisation.JSONSerialisation import JSONSerialisation
#from speedysvc.serialisation.ArrowSerialisation import ArrowSerialisation
from speedysvc.serialisation.PickleSerialisation import PickleSerialisation
from speedysvc.serialisation.MarshalSerialisation import MarshalSerialisation
from speedysvc.serialisation.MsgPackSerialisation import MsgPackSerialisation

__serialisers = [
    RawSerialisation,
    JSONSerialisation,
    #ArrowSerialisation,
    PickleSerialisation,
    MarshalSerialisation,
    MsgPackSerialisation,
]

__by_name_dict = {}
for __serialiser in __serialisers:
    assert not __serialiser.name in __by_name_dict, __serialiser.name
    __by_name_dict[__serialiser.name] = __serialiser


def get_by_name(code: str):
    return __by_name_dict[code]

