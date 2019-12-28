from mmap import mmap

from .ReadStrArray import ReadStrArray
from .NumArray import NumArray


DMMap = {}


def read_array(f, L):
    assert 'b' in f.mode, "file `f` not opened in binary mode"
    typecode, seek, amount = L

    if not f in DMMap:
        try:
            DMMap[f] = mmap(f.fileno(), 0)
        except OSError:
            import warnings
            # OSError: [Errno 22] Invalid argument?
            # some filesystems can't use mmap,
            # e.g. network shares
            from warnings import warn
            from traceback import print_exc
            warn("Warning: couldn't memory map file %s - performance will be slow" % f)
            #print_exc()
        except ValueError:
            # "cannot mmap an empty file" (?)
            return [] # WARNING!

    if f in DMMap:
        f = DMMap[f]

    if typecode == 'utf-8':
        return ReadStrArray(f, seek, amount)
    else:
        return NumArray(dtype=typecode, buffer=f, offset=seek, shape=(amount,))
