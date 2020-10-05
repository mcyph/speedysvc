import mmap
import time
import struct
import ctypes
import io
import _thread
import weakref
from time import sleep

from ctypes import wintypes

INVALID = 0

# https://stackoverflow.com/questions/31495461/mmap-cant-attach-to-existing-region-without-knowing-its-size-windows
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

FILE_MAP_ALL_ACCESS = 0x001f


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = (('BaseAddress', wintypes.LPVOID),
                ('AllocationBase', wintypes.LPVOID),
                ('AllocationProtect', wintypes.DWORD),
                ('RegionSize', ctypes.c_size_t),
                ('State', wintypes.DWORD),
                ('Protect', wintypes.DWORD),
                ('Type', wintypes.DWORD))


PMEMORY_BASIC_INFORMATION = ctypes.POINTER(MEMORY_BASIC_INFORMATION)

kernel32.VirtualQuery.restype = ctypes.c_size_t
kernel32.VirtualQuery.argtypes = (wintypes.LPCVOID, PMEMORY_BASIC_INFORMATION, ctypes.c_size_t)

kernel32.OpenFileMappingW.restype = wintypes.HANDLE
kernel32.OpenFileMappingW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)

kernel32.MapViewOfFile.restype = wintypes.LPVOID
kernel32.MapViewOfFile.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t)

kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)


def get_mmap_tagname_size(tagname):
    #print("REGION SIZE:", tagname)
    hMap = kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, tagname)
    pBuf = kernel32.MapViewOfFile(hMap, FILE_MAP_ALL_ACCESS, 0, 0, 0)
    kernel32.CloseHandle(hMap)

    mbi = MEMORY_BASIC_INFORMATION()
    kernel32.VirtualQuery(pBuf, ctypes.byref(mbi), mmap.PAGESIZE)
    return mbi.RegionSize


def _runme():
    while True:
        clean_out = False

        for shm_inst_ref in _shm_insts:
            shm_inst = shm_inst_ref()
            try:
                if shm_inst is None:
                    clean_out = True
                elif shm_inst[0] == INVALID:
                    shm_inst._reconnect()
            except (AttributeError, IndexError, ValueError):
                pass

        if clean_out:
            _shm_insts[:] = [i for i in _shm_insts if i() is not None]

        time.sleep(0.1)


_thread.start_new_thread(_runme, ())
_shm_insts = []


class Win32SHM:
    def __init__(self, location, create, new_size=None):
        self.tagname = 'ssvc_%s' % location.decode('ascii')
        self._lock = _thread.allocate_lock()

        if create:
            self._create(new_size)
        else:
            self._connect()

        _shm_insts.append(weakref.ref(self))

    def _create(self, new_size):
        assert new_size is not None
        new_size = self.__get_size(new_size)

        while True:
            try:
                memory = mmap.mmap(-1,
                                   length=new_size,
                                   tagname=self.tagname,
                                   access=mmap.ACCESS_WRITE)
                break
            except PermissionError:
                time.sleep(0.01)

        memory[0] = 1
        self.memory = memory

    def _connect(self):
        while True:
            memory = mmap.mmap(-1,
                               length=get_mmap_tagname_size(self.tagname),
                               tagname=self.tagname,
                               access=mmap.ACCESS_WRITE)

            if memory[0] == INVALID:
                memory.close()
                time.sleep(0.01)
                continue
            else:
                break

        self.memory = memory

    def _reconnect(self):
        # Emulate access to the old data by copying
        # it before we can open the new data
        old_memory = self.memory
        self.memory = old_memory[:]
        old_memory.close()

        self._connect()

    def __get_size(self, size):
        chk_size = mmap.PAGESIZE
        while chk_size < size:
            chk_size *= 2
        assert chk_size >= size
        return chk_size

    def __len__(self):
        return len(self.memory)

    def __getitem__(self, item):
        return self.memory[item]

    def __setitem__(self, key, value):
        self.memory[key] = value

    def close(self):
        try:
            self.memory.close()
        except AttributeError:
            pass
