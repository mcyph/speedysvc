from array import array
from .WriteStrArray import WriteStrArray

"""
Get arrays for writing in ArrayUtils

(I'm doing this to allow potential modifications,
e.g. a drop-in replacement array etc later)
"""


def get_array_by_type(typ):
    if typ in 'cu':
        return get_uni_array()
    elif typ in 'bBhHiIlL':
        return get_int_array()
    elif typ in 'f':
        return get_float_array()
    elif typ in 'd':
        return get_double_array()
    else:
        raise Exception("unknown type: %s" % typ)


def get_int_array(signed=True):
    if signed:
        return array('l')
    else:
        return array('L')


def get_uni_array():
    return WriteStrArray()


def get_float_array():
    return array('f')


def get_double_array():
    return array('d')
