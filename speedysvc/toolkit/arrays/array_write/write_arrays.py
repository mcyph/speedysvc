from .write_array import write_array


def write_arrays(f, L):
    if isinstance(L, dict):
        L = list(L.items())

    return_list = []
    for key, iL in L:
        return_list.append((key, write_array(f, iL)))
    return return_list
