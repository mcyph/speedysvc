from .write_array import write_array


def write_arrays(f, L):
    if isinstance(L, dict):
        L = list(L.items())

    LRtn = []
    for key, iL in L:
        LRtn.append((key, write_array(f, iL)))
    return LRtn
