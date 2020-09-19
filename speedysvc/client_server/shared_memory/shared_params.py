import sys
import mmap


if sys.platform == 'win32':
    import struct
    import ctypes
    from ctypes import wintypes

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


    def unlink_shared_memory(location):
        pass  # TODO!!!! =======================================================================================================


    _flip_ids = {}

    def get_mmap(location, create, new_size=None):
        #print("GET MMAP:", location, create)

        _flip_ids[location] = not _flip_ids.get(location, True)
        location = 'ssvc%s_' % int(_flip_ids[location]) + location.decode('ascii')

        if new_size is not None:
            chk_size = mmap.PAGESIZE
            while chk_size < new_size:
                chk_size *= 2
            assert chk_size >= new_size
            new_size = chk_size

        if create:
            assert new_size is not None
            memory = mmap.mmap(-1,
                               length=new_size,
                               tagname=location,
                               access=mmap.ACCESS_WRITE)
            if any(memory[:]):
                raise Exception("Memory should be all zeroes!")
        else:
            memory = mmap.mmap(-1,
                               length=get_mmap_tagname_size(location),
                               tagname=location,
                               access=mmap.ACCESS_WRITE)
        return memory

else:
    import posix_ipc
    from posix_ipc import unlink_shared_memory as _usm

    def unlink_shared_memory(location):
        try:
            _usm(location)
        except posix_ipc.ExistentialError:
            raise FileNotFoundError(location)

    def get_mmap(location, create, new_size=None):
        try:
            if create:
                assert new_size is not None

                # Make sure the size is a power of the OS's
                # page size - doesn't make sense to allocate less
                # (in all cases I can think of using it)
                chk_size = posix_ipc.PAGE_SIZE
                while chk_size < new_size:
                    chk_size *= 2
                assert chk_size >= new_size

                # Clean up since last time
                try:
                    posix_ipc.unlink_shared_memory(location.decode('ascii'))
                except posix_ipc.ExistentialError:
                    pass

                # Allocate the memory map
                memory = posix_ipc.SharedMemory(
                    location.decode('ascii'), posix_ipc.O_CREX, size=chk_size # O_CREX?
                )
                assert memory.size == chk_size, (memory.size, chk_size)
                mapfile = mmap.mmap(memory.fd, memory.size)

                # We (apparently) don't need the file
                # descriptor after it's been memory mapped
                memory.close_fd()

                return mapfile
            else:
                # Connect to the existing memory map
                #print("CONNECT TO SHARED MEMORY:", location)
                memory = posix_ipc.SharedMemory(location.decode('ascii'))

                mapfile = mmap.mmap(memory.fd, memory.size)
                memory.close_fd()
                return mapfile

        except posix_ipc.ExistentialError:
            raise FileExistsError(location)


INVALID = b'I'[0]
SERVER = b'S'[0]
CLIENT = b'C'[0]

if __name__ == '__main__':
    map_1 = get_mmap(b'service_5555_pids', True, 32768)
    map_2 = get_mmap(b'service_5555_pids', False, 32768)
