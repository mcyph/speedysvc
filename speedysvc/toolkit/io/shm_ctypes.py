import os
import stat
import ctypes
from ctypes import CDLL

rtld = CDLL('librt.so', use_errno=True)
_shm_open = rtld.shm_open
_shm_unlink = rtld.shm_unlink

unicode = str


def shm_open(name, mode, flags=stat.S_IRUSR | stat.S_IWUSR, initial_size=None):
    """
    mode: os.O_RDWR | os.O_CREAT | os.O_EXCL to create a new block
    mode: os.O_RDWR to open an existing block
    """
    print(name)
    if isinstance(name, bytes):
        name = ctypes.create_string_buffer(name)
    elif isinstance(name, unicode):
        name = ctypes.create_unicode_buffer(name)
    else:
        raise TypeError("`name` must be `bytes` or `unicode`")

    result = _shm_open(
        name,
        ctypes.c_int(mode),
        ctypes.c_ushort(flags)
    )

    if result == -1:
        raise RuntimeError(os.strerror(ctypes.get_errno()))

    if initial_size:
        print("TRUNCATING TO:", initial_size)
        os.ftruncate(result, initial_size)

    return result


def shm_unlink(name):
    if isinstance(name, bytes):
        name = ctypes.create_string_buffer(name)
    elif isinstance(name, unicode):
        name = ctypes.create_unicode_buffer(name)
    else:
        raise TypeError("`name` must be `bytes` or `unicode`")

    result = _shm_unlink(name)

    if result == -1:
        raise RuntimeError(os.strerror(ctypes.get_errno()))


