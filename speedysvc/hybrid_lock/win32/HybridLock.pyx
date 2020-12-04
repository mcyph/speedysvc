"""
Named mutex handling (for Win32).

Licensed under the MIT license by Ben Hoyt 2011
URL: https://code.activestate.com/recipes/577794-win32-named-mutex-class-for-system-wide-mutex/

Modifications by Dave Morrissey 2020
"""

from libc.string cimport memcpy
from HybridLock cimport *


# cython refuses to compile unless this is here
STUFF = "hi"


cdef DWORD FILE_MAP_ALL_ACCESS = 0xF001F
cdef DWORD STANDARD_RIGHTS_REQUIRED = 0xF0000
cdef DWORD SYNCHRONIZE = 0x100000
cdef DWORD MUTANT_QUERY_STATE = 0x1
cdef DWORD SEMAPHORE_MODIFY_STATE = 0x0002
cdef DWORD MUTEX_ALL_ACCESS = STANDARD_RIGHTS_REQUIRED | SYNCHRONIZE | MUTANT_QUERY_STATE
cdef DWORD WAIT_OBJECT_0 = 0
cdef DWORD WAIT_TIMEOUT = 0x102
cdef DWORD WAIT_ABANDONED = 0x80
cdef DWORD ERROR_INVALID_PARAMETER = 0x57
cdef DWORD STILL_ACTIVE = 259
cdef DWORD PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

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

cdef unsigned char LOCKED = 1
cdef unsigned char UNLOCKED = 2
cdef unsigned char DESTROYED = 3  # STUB!

# spin lock char, process query lock, process holding lock
cdef int SPINLOCK_IDX = 0
#cdef const int PROCESS_QUERY_LOCK = 1
cdef int PROCESS_HOLDING_LOCK = 2


cdef uint64_t get_time():
    cdef FILETIME ft
    cdef uint64_t fileTime64;
    GetSystemTimeAsFileTime(&ft)

    memcpy(&fileTime64, &ft, sizeof(uint64_t))
    return fileTime64


cdef int pid_is_running(DWORD pid):
    cdef HANDLE process_handle
    cdef DWORD exitCode

    if pid == 0: return 1
    elif pid < 0: return 0

    process_handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid)
    if process_handle == NULL:
        if GetLastError() == ERROR_INVALID_PARAMETER:
            return 0
        return -1

    if GetExitCodeProcess(process_handle, &exitCode):
        CloseHandle(process_handle)
        return exitCode == STILL_ACTIVE

    CloseHandle(process_handle)
    return -1


cdef class HybridLock(object):
    cdef HANDLE handle
    cdef HANDLE mmap_handle
    cdef LPVOID _mmap
    cdef int * _process_holding_lock
    cdef unsigned char * _lock_status

    cdef public:
        object name

    def __init__(self, name, mode, initial_value=1, permissions=0o0666):
        """
        Create named mutex with given name, also acquiring mutex if acquired is True.
        Mutex names are case sensitive, and a filename (with backslashes in it) is not a
        valid mutex name. Raises WindowsError on error.
        """
        self.name = name
        name = name.decode('ascii')
        cdef HANDLE ret
        cdef unsigned char * lock_status

        # Open or create the named semaphore
        if mode == CONNECT_TO_EXISTING:
            ret = OpenSemaphoreW(DEFAULT_MODE, 0, name)
            if not ret: raise NoSuchSemaphoreException()
        elif mode == CONNECT_OR_CREATE:
            ret = OpenSemaphoreW(DEFAULT_MODE, 0, name) or \
                  CreateSemaphoreW(NULL, 1, 1, name)
        elif mode == CREATE_NEW_EXCLUSIVE:
            #ret = OpenSemaphoreW(DEFAULT_MODE, 0, name)
            #if ret: raise SemaphoreExistsException(name)
            ret = CreateSemaphoreW(NULL, 1, 1, name)
        elif mode == CREATE_NEW_OVERWRITE:
            ret = CreateSemaphoreW(NULL, 1, 1, name)
        else:
            raise Exception(mode)

        self.handle = ret
        assert initial_value == 1  # HACK!

        if mode in (CREATE_NEW_OVERWRITE, CREATE_NEW_EXCLUSIVE):
            # Try to reset the semaphore if it still exists
            try:
                ReleaseSemaphore(self.handle, 1, NULL)
            except (WindowsError, RuntimeError):
                pass

        # Open or create the shared memory
        name = ("Local\\ssvclk_%s" % name).encode('ascii')

        if mode == CREATE_NEW_EXCLUSIVE or mode == CREATE_NEW_OVERWRITE:
            self.mmap_handle = CreateFileMapping(<HANDLE>-1, NULL, PAGE_READWRITE, 0, 0x1000, <char *>name)

            if self.mmap_handle == NULL:
                if (GetLastError() == ERROR_INVALID_HANDLE):
                    raise SemaphoreExistsException(name)
                else:
                    raise OSError(GetLastError())
            #elif mode == CREATE_NEW_EXCLUSIVE and GetLastError() == ERROR_ALREADY_EXISTS:
            #    raise SemaphoreExistsException(name)

        elif mode == CONNECT_OR_CREATE:
            self.mmap_handle = OpenFileMapping(FILE_MAP_ALL_ACCESS, TRUE, <char*>name)
            if self.mmap_handle == NULL:
                self.mmap_handle = CreateFileMapping(<HANDLE>-1, NULL, PAGE_READWRITE, 0, 0x1000, <char *>name)
                if self.mmap_handle == NULL:
                    raise OSError(GetLastError())

        elif mode == CONNECT_TO_EXISTING:
            self.mmap_handle = OpenFileMapping(FILE_MAP_ALL_ACCESS, TRUE, <char *>name)
            if self.mmap_handle == NULL:
                raise OSError(GetLastError())
        else:
            raise Exception(mode)

        self._mmap = MapViewOfFile(self.mmap_handle, FILE_MAP_ALL_ACCESS, 0, 0, <SIZE_T>0x1000)
        if self._mmap == NULL:
            raise OSError(GetLastError())

        lock_status = <unsigned char *>self._mmap
        if mode == CREATE_NEW_EXCLUSIVE and not (lock_status[0] == 0 or lock_status[0] == DESTROYED):
            raise SemaphoreExistsException(name)
        if mode == CREATE_NEW_OVERWRITE or mode == CREATE_NEW_EXCLUSIVE:
            lock_status[0] = UNLOCKED
        if mode == CONNECT_TO_EXISTING and lock_status[0] == DESTROYED:
            raise NoSuchSemaphoreException(name)

        #self._mmap[PROCESS_QUERY_LOCK] = UNLOCKED
        self._process_holding_lock = &(<int *>self._mmap)[PROCESS_HOLDING_LOCK]

        if self._process_holding_lock[0] and pid_is_running(self._process_holding_lock[0]) == 0:
            try:
                self.unlock()
            except OSError:
                pass

    def __del__(self):
        self.close()

    def get_pid_holding_lock(self):
        """
        Warning: This is not strictly threadsafe!!
        This method is mainly used when cleaning up resources
        """
        if self.get_value() == UNLOCKED:
            return None

        return self._process_holding_lock[0]

    def destroy(self):
        """
        Make the lock unusable for this and other processes
        """
        cdef unsigned char * lock_status = <unsigned char *>self._mmap

        if lock_status[0] == DESTROYED:
            # Already destroyed!
            self.close()
            return
        else:
            try:
                self.unlock()
            except (WindowsError, RuntimeError):
                pass

            lock_status[0] = DESTROYED
            self._process_holding_lock[0] = 0
            self.close()

    def close(self):
        """
        Close the mutex and release the handle.
        """
        if self.handle == NULL or self.mmap_handle == NULL:
            # Already closed
            return

        ret = CloseHandle(self.handle)
        if not ret:
            raise OSError(GetLastError())

        ret = UnmapViewOfFile(self._mmap)
        if not ret:
            raise OSError(GetLastError())

        ret = CloseHandle(self.mmap_handle)
        if not ret:
            raise OSError(GetLastError())

        self.handle = NULL
        self.mmap_handle = NULL
        self._mmap = NULL

    def get_value(self):
        """
        Get the current value: 1 for unlocked and 0 for locked
        This can be unreliable, as the value could change during calling
        """
        cdef unsigned char * lock_status = <unsigned char *>self._mmap
        if lock_status[0] == DESTROYED:
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
        cdef unsigned char * lock_status = <unsigned char *>self._mmap
        if lock_status[0] == DESTROYED:
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
        cdef uint64_t t1
        cdef uint64_t t2
        cdef unsigned char * lock_status = <unsigned char *>self._mmap

        if timeout is None:
            timeout = -1

        if timeout == -1:
            # Wait forever (INFINITE)
            _timeout = 0xFFFFFFFF
        else:
            _timeout = int(round(timeout * 1000))

        if lock_status[0] == DESTROYED:
            raise SemaphoreDestroyedException()

        # Very basic in-python spinlock
        # All its meant to do is reduce the probability calling WaitForSingleObject
        # will cause the process slice scheduler to put this process to the back
        # It would be better to do this in cython, though would prefer to not
        # require a C compiler on Windows

        if spin:
            t1 = get_time()

            while lock_status[0] == LOCKED:
                t2 = get_time()

                if t2-t1 > 15000:
                    # Windows time slice is 15 milliseconds tops
                    break

            lock_status[0] = LOCKED

        with nogil:
            ret = WaitForSingleObject(handle, _timeout)

        if ret == 0:
            # normally acquired (0)
            self._process_holding_lock[0] = _getpid()
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
        cdef unsigned char * lock_status = <unsigned char *>self._mmap

        if lock_status[0] == DESTROYED:
            raise SemaphoreDestroyedException()
        lock_status[0] = UNLOCKED

        with nogil:
            ret = ReleaseSemaphore(handle, 1, NULL)

            if not ret:
                raise OSError(GetLastError())
