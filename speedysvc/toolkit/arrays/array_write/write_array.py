from .WriteStrArray import WriteStrArray
from .consts import LInt, LUInt


def write_array(f, L):
    """
    Write `array.array` object `L` to disk, returning the info needed
    to read with `read_array`
    """
    import numpy # Need to use numpy directly, if writing
    assert 'b' in f.mode, "file `f` not opened in binary mode"
    num_items = len(L)

    if isinstance(L, WriteStrArray):
        # String/unicode types
        dtyp = 'utf-8'
        a = L

    elif L.typecode in 'lL':
        # Integer/long types
        if L:
            max_ = max(L)
            min_ = min(L)
        else:
            max_ = min_ = 0

        for typ, from_, to in (
            LInt if min_ < 0 else LUInt
        ):
            #print max_, min_, from_, to

            if (min_ >= from_) and (max_ <= to):
                dtyp = typ
                break

        a = numpy.ndarray(
            buffer=numpy.array(L, dtype=dtyp), dtype=dtyp, shape=(num_items,)
        )
        #print 'WRITE:', a
    elif L.typecode in 'fd':
        # Float/double types
        dtyp = {
            'f': 'float32',
            'd': 'float64'
        }[L.typecode]

        a = numpy.ndarray(
            buffer=numpy.array(L, dtype=dtyp), dtype=dtyp, shape=(num_items,)
        )
    else:
        raise Exception("unhandled typecode: %s" % L.typecode)

    offset = f.tell()
    a.tofile(f)
    amount = (f.tell()-offset) // a.itemsize
    assert amount == num_items
    #print 'AMOUNT:', amount, a
    return [dtyp, offset, amount]
