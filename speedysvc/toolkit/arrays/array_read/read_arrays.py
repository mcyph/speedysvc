from .read_array import read_array


def read_arrays(f, L):
    """
    An array list with various possible types (str/unicode/
    unsigned short/unsigned integer) as used in indices
    e.g. {'Page': 555, 'Character': 'A', ...}
    """

    DKeys = {}
    LOrder = []

    for key, iL in L:
        DKeys[key] = read_array(f, iL)
        LOrder.append(key)

    return LOrder, DKeys
