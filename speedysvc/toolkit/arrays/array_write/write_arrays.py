from .write_array import write_array


def write_arrays(f, L):
    if isinstance(L, dict):
        L = list(L.items())

    rtn_list = []
    for key, iL in L:
        rtn_list.append((key, write_array(f, iL)))
    return rtn_list
