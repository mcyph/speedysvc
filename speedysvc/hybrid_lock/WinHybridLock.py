"""
Named mutex handling (for Win32).

Licensed under the MIT license by Ben Hoyt 2011
URL: https://code.activestate.com/recipes/577794-win32-named-mutex-class-for-system-wide-mutex/

Modifications by David Morrissey 2020
"""

from os import getpid
import mmap
from time import time
import ctypes
import struct
import _thread
from ctypes import wintypes


FILE_MAP_ALL_ACCESS = 0xF001F
STANDARD_RIGHTS_REQUIRED = 0xF0000
SYNCHRONIZE = 0x100000
MUTANT_QUERY_STATE = 0x1
SEMAPHORE_MODIFY_STATE = 0x0002
MUTEX_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | MUTANT_QUERY_STATE
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
WAIT_ABANDONED = 0x80

# Create ctypes wrapper for Win32 functions we need, with correct argument/return types
_CreateSemaphore = ctypes.windll.kernel32.CreateSemaphoreW
_CreateSemaphore.argtypes = [wintypes.LPVOID, wintypes.LONG, wintypes.LONG, wintypes.LPWSTR]
_CreateSemaphore.restype = wintypes.HANDLE

_OpenSemaphore = ctypes.windll.kernel32.OpenSemaphoreW
_OpenSemaphore.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPWSTR]
_OpenSemaphore.restype = wintypes.HANDLE

_WaitForSingleObject = ctypes.windll.kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_WaitForSingleObject.restype = wintypes.DWORD

_ReleaseSemaphore = ctypes.windll.kernel32.ReleaseSemaphore
_ReleaseSemaphore.argtypes = [wintypes.HANDLE, wintypes.LONG, wintypes.LPLONG]
_ReleaseSemaphore.restype = wintypes.BOOL

_CloseHandle = ctypes.windll.kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE]
_CloseHandle.restype = wintypes.BOOL


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


class WinHybridLock(object):
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
        self.handle = None
        self.__lock = _thread.allocate_lock()

        if mode == CONNECT_TO_EXISTING:
            ret = _OpenSemaphore(SYNCHRONIZE|SEMAPHORE_MODIFY_STATE, False, name.decode('utf-8'))
            if not ret: raise NoSuchSemaphoreException()
        elif mode == CONNECT_OR_CREATE:
            ret = _OpenSemaphore(SYNCHRONIZE|SEMAPHORE_MODIFY_STATE, False, name.decode('utf-8')) or \
                  _CreateSemaphore(None, 1, 1, name.decode('utf-8'))
        elif mode == CREATE_NEW_EXCLUSIVE:
            ret = _OpenSemaphore(SYNCHRONIZE|SEMAPHORE_MODIFY_STATE, False, name.decode('utf-8'))
            if ret: raise SemaphoreExistsException(name.decode('utf-8'))
            ret = _CreateSemaphore(None, 1, 1, name.decode('utf-8'))
        elif mode == CREATE_NEW_OVERWRITE:
            ret = _CreateSemaphore(None, 1, 1, name.decode('utf-8'))
        else:
            raise Exception(mode)

        self.handle = ret
        assert initial_value == UNLOCKED  # HACK!

        if mode in (CREATE_NEW_OVERWRITE, CREATE_NEW_EXCLUSIVE):
            try:
                _ReleaseSemaphore(self.handle, 1, None)
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
        self._mmap[0] = DESTROYED

    def close(self):
        """
        Close the mutex and release the handle.
        """
        if self.handle is None:
            # Already closed
            return
        ret = _CloseHandle(self.handle)
        if not ret:
            raise OSError()
        self.handle = None

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

    def lock(self, timeout=None, spin=1):
        """
        Acquire ownership of the mutex, returning True if acquired. If a timeout
        is specified, it will wait a maximum of timeout seconds to acquire the mutex,
        returning True if acquired, False on timeout. Raises WindowsError on error.
        """
        # print("LOCK:", self.name, timeout)

        if self._mmap[0] == DESTROYED:
            raise SemaphoreDestroyedException()

        if timeout == -1:
            timeout = None

        # Very basic in-python spinlock
        # All its meant to do is reduce the probability calling WaitForSingleObject
        # will cause the process slice scheduler to put this process to the back
        # It would be better to do this in cython, though would prefer to not
        # require a C compiler on Windows

        if spin:
            t = time()
            while True:
                if self._mmap[0] == UNLOCKED:
                    self._mmap[0] = LOCKED
                    break
                elif time()-t > 0.015:
                    # Windows time slice is 15 milliseconds tops
                    break

        if timeout is None:
            # Wait forever (INFINITE)
            timeout = 0xFFFFFFFF
        else:
            timeout = int(round(timeout * 1000))

        ret = _WaitForSingleObject(self.handle, timeout)

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
        if self._mmap[0] == DESTROYED:
            raise SemaphoreDestroyedException()
        self._mmap[0] = UNLOCKED

        ret = _ReleaseSemaphore(self.handle, 1, None)
        if not ret:
            raise OSError(ctypes.GetLastError())


if __name__ == '__main__':
    lock = WinHybridLock(b"my semaphore", CONNECT_OR_CREATE)
    lock.lock()

    try:
        lock.lock(1)
    except TimeoutError:
        pass

    lock2 = WinHybridLock(b"my semaphore", CONNECT_TO_EXISTING)

    #lock2.lock()
    #print("SHOULDN'T GET HERE!")

    lock.unlock()
    lock.lock()
    lock.unlock()
    lock.lock(1)
    #lock.lock(1)
