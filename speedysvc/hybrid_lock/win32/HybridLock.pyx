"""
Named mutex handling (for Win32).

Licensed under the MIT license by Ben Hoyt 2011
URL: https://code.activestate.com/recipes/577794-win32-named-mutex-class-for-system-wide-mutex/

Modifications by David Morrissey 2020
"""

import mmap
import struct
#import cython
#import time
from os import getpid
from libc.time cimport time,time_t
from HybridLock cimport *


cdef DWORD FILE_MAP_ALL_ACCESS = 0xF001F
cdef DWORD STANDARD_RIGHTS_REQUIRED = 0xF0000
cdef DWORD SYNCHRONIZE = 0x100000
cdef DWORD MUTANT_QUERY_STATE = 0x1
cdef DWORD SEMAPHORE_MODIFY_STATE = 0x0002
cdef DWORD MUTEX_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | MUTANT_QUERY_STATE
cdef DWORD WAIT_OBJECT_0 = 0
cdef DWORD WAIT_TIMEOUT = 0x102
cdef DWORD WAIT_ABANDONED = 0x80

cdef DWORD DEFAULT_MODE = SYNCHRONIZE|SEMAPHORE_MODIFY_STATE


# TODO: PROVIDE SUPPORT FOR THESE CONDITIONS!!!! =======================================================================
class SemaphoreExistsException(Exception):
    pass

class NoSuchSemaphoreException(Exception):
    pass

class SemaphoreDestroyedException(Exception):
    pass


CONNECT_OR_CREATE = 0
CONNECT_TO_EXISTING = 1
CREATE_NEW_OVERWRITE = 2
CREATE_NEW_EXCLUSIVE = 3

LOCKED = 0
UNLOCKED = 1
DESTROYED = 2  # STUB!

# spin lock char, process query lock, process holding lock
SPINLOCK_IDX = 0
PROCESS_QUERY_LOCK = 1
PROCESS_HOLDING_LOCK = 2
PROCESS_HOLDING_ENC = struct.Struct('@l')

STUFF = "hi"

cdef uint64_t get_time():
    cdef FILETIME ft
    cdef LARGE_INTEGER li

    GetSystemTimeAsFileTime(&ft)
    li.LowPart = ft.dwLowDateTime
    li.HighPart = ft.dwHighDateTime

    cdef uint64_t ret = li.QuadPart
    ret /= 10000
    return ret


cdef class HybridLock(object):
    cdef HANDLE handle

    cdef public:
        object name, _mmap

    """A named, system-wide mutex that can be acquired and released."""
    # sem_loc, int mode,
    #                   int initial_value=UNLOCKED,
    #                   int permissions=0666
    def __init__(self, name, mode, initial_value=UNLOCKED, permissions=0o0666):
        """
        Create named mutex with given name, also acquiring mutex if acquired is True.
        Mutex names are case sensitive, and a filename (with backslashes in it) is not a
        valid mutex name. Raises WindowsError on error.
        """
        self.name = name
        cdef HANDLE ret

        if mode == CONNECT_TO_EXISTING:
            ret = OpenSemaphoreW(DEFAULT_MODE, 0, name.decode('ascii'))
            if not ret: raise NoSuchSemaphoreException()
        elif mode == CONNECT_OR_CREATE:
            ret = OpenSemaphoreW(DEFAULT_MODE, 0, name.decode('ascii')) or \
                  CreateSemaphoreW(NULL, 1, 1, name.decode('ascii'))
        elif mode == CREATE_NEW_EXCLUSIVE:
            ret = OpenSemaphoreW(DEFAULT_MODE, 0, name.decode('ascii'))
            if ret: raise SemaphoreExistsException(name.decode('ascii'))
            ret = CreateSemaphoreW(NULL, 1, 1, name.decode('ascii'))
        elif mode == CREATE_NEW_OVERWRITE:
            ret = CreateSemaphoreW(NULL, 1, 1, name.decode('ascii'))
        else:
            raise Exception(mode)

        self.handle = ret
        assert initial_value == UNLOCKED  # HACK!

        if mode in (CREATE_NEW_OVERWRITE, CREATE_NEW_EXCLUSIVE):
            try:
                ReleaseSemaphore(self.handle, 1, NULL)
            except (WindowsError, RuntimeError):
                pass

        self._mmap = mmap.mmap(-1,
                               length=mmap.PAGESIZE,
                               tagname='ssvclk_'+name.decode('utf-8'),
                               access=mmap.ACCESS_WRITE)
        if not self._mmap[0]:
            self._mmap[0] = UNLOCKED
            self._mmap[PROCESS_QUERY_LOCK] = UNLOCKED

    def get_pid_holding_lock(self):
        """
        Warning: This is not strictly threadsafe!!
        This method is mainly used when cleaning up resources
        """
        if self.get_value() == UNLOCKED:
            return None

        return PROCESS_HOLDING_ENC.unpack(
            self._mmap[PROCESS_HOLDING_LOCK:PROCESS_HOLDING_LOCK+PROCESS_HOLDING_ENC.size]
        )[0]

    def destroy(self):
        """
        Make the lock unusable for this and other processes
        """
        if self._mmap[0] == DESTROYED:
            # Already destroyed!
            return

        try:
            self.unlock()
        except (WindowsError, RuntimeError):
            pass
        self.close()
        self._mmap[0] = bytes([DESTROYED])

    def close(self):
        """
        Close the mutex and release the handle.
        """
        if self.handle == NULL:
            # Already closed
            return
        ret = CloseHandle(self.handle)
        if not ret:
            raise OSError()
        self.handle = NULL

    def get_value(self):
        """
        Get the current value: 1 for unlocked and 0 for locked
        This can be unreliable, as the value could change during calling
        """
        if self._mmap[0] == DESTROYED:
            raise SemaphoreDestroyedException()

        try:
            self.lock(0)
            self.unlock()
            return 1
        except TimeoutError:
            return 0

    def __repr__(self):
        """
        Return the Python representation of this mutex.
        """
        if self._mmap[0] == DESTROYED:
            return "(Destroyed WinHybridLock)"

        return '{0}({1!r}, acquired={2})'.format(
            self.__class__.__name__, self.name, self.get_value())

    __del__ = close
    __str__ = __repr__

    def lock(self, timeout=-1, int spin=1):
        """
        Acquire ownership of the mutex, returning True if acquired. If a timeout
        is specified, it will wait a maximum of timeout seconds to acquire the mutex,
        returning True if acquired, False on timeout. Raises WindowsError on error.
        """
        # print("LOCK:", self.name, timeout)
        cdef DWORD ret
        cdef HANDLE handle = self.handle
        cdef DWORD _timeout
        cdef uint64_t t1, t2

        if timeout is None:
            timeout = -1

        if timeout == -1:
            # Wait forever (INFINITE)
            _timeout = 0xFFFFFFFF
        else:
            _timeout = int(round(timeout * 1000))

        if self._mmap[0] == DESTROYED:
            raise SemaphoreDestroyedException()

        # Very basic in-python spinlock
        # All its meant to do is reduce the probability calling WaitForSingleObject
        # will cause the process slice scheduler to put this process to the back
        # It would be better to do this in cython, though would prefer to not
        # require a C compiler on Windows

        #if spin:
        #    t1 = get_time()

        #    _mmap = self._mmap
        #    _getitem = _mmap.__getitem__

        #    while _getitem(0) == LOCKED:
        #        t2 = get_time()

        #        if t2-t1 > 15:
                    # Windows time slice is 15 milliseconds tops
        #            break

        #    _mmap[0] = bytes([LOCKED])

        with nogil:
            ret = WaitForSingleObject(handle, _timeout)

        if ret == 0:
            # normally acquired (0)
            self._mmap[PROCESS_HOLDING_LOCK:PROCESS_HOLDING_LOCK+PROCESS_HOLDING_ENC.size] = \
                PROCESS_HOLDING_ENC.pack(getpid())
            return True
        elif ret == 0x102:
            # Timeout
            raise TimeoutError()
        else:
            # 0x80 -> another owning process terminating without releasing (0x80)
            # Waiting failed
            raise OSError()  #ctypes.WinError()

    def unlock(self):
        """
        Release an acquired mutex. Raises WindowsError on error.
        """
        cdef BOOL ret
        cdef HANDLE handle = self.handle

        if self._mmap[0] == DESTROYED:
            raise SemaphoreDestroyedException()
        self._mmap[0] = bytes([UNLOCKED])

        with nogil:
            ret = ReleaseSemaphore(handle, 1, NULL)

            if not ret:
                raise OSError(GetLastError())


#if __name__ == '__main__':
#    lock = WinHybridLock(b"my semaphore", CONNECT_OR_CREATE)
#    lock.lock()

#    try:
#        lock.lock(1)
#    except TimeoutError:
#        pass

#    lock2 = WinHybridLock(b"my semaphore", CONNECT_TO_EXISTING)

    #lock2.lock()
    #print("SHOULDN'T GET HERE!")

#    lock.unlock()
#    lock.lock()
#    lock.unlock()
#    lock.lock(1)
    #lock.lock(1)
