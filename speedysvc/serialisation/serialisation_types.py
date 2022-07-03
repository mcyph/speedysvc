from RawSerialisation import RawSerialisation
from JSONSerialisation import JSONSerialisation
from ArrowSerialisation import ArrowSerialisation
from PickleSerialisation import PickleSerialisation
from MarshalSerialisation import MarshalSerialisation
from MsgPackSerialisation import MsgPackSerialisation

__serialisers = [
    RawSerialisation,
    JSONSerialisation,
    ArrowSerialisation,
    PickleSerialisation,
    MarshalSerialisation,
    MsgPackSerialisation,
]

__by_name_dict = {}
for __serialiser in __serialisers:
    assert not __compressor.name in __by_name_dict, __serialiser.typecode
    __by_name_dict[__compressor.typecode] = __serialiser


def get_by_name(code: str):
    return __by_name_dict[code]

