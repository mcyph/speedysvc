import posix_ipc
import mmap


def get_mmap(location, create, new_size=None):
    if create:
        assert new_size is not None

        # Make sure the size is a power of the OS's
        # page size - doesn't make sense to allocate less
        # (in all cases I can think of using it)
        chk_size = posix_ipc.PAGE_SIZE
        while chk_size < new_size:
            chk_size *= 2

        # Clean up since last time
        try:
            #print("UNLINKING:", location)
            posix_ipc.unlink_shared_memory(location.decode('ascii'))
        except:
            pass
            #import traceback
            #traceback.print_exc()

        # Allocate the memory map
        memory = posix_ipc.SharedMemory(
            location.decode('ascii'), posix_ipc.O_CREX, size=chk_size # O_CREX?
        )
        mapfile = mmap.mmap(memory.fd, memory.size)
        #print(f"{location} ALLOCATING:", chk_size, "ACTUALLY:", memory.size)

        # We (apparently) don't need the file
        # descriptor after it's been memory mapped
        memory.close_fd()
        return mapfile
    else:
        # Connect to the existing memory map
        memory = posix_ipc.SharedMemory(location.decode('ascii'))
        #print("CONNECT TO MEMORY SIZE:", location, memory.size)
        mapfile = mmap.mmap(memory.fd, memory.size)
        memory.close_fd()
        return mapfile


INVALID = b'I'[0]
SERVER = b'S'[0]
CLIENT = b'C'[0]
PENDING = b'P'[0]

if __name__ == '__main__':
    map_1 = get_mmap(b'service_5555_pids', True, 32768)
    map_2 = get_mmap(b'service_5555_pids', False, 32768)