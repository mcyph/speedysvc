import mmap
import struct
import posix_ipc
from network_tools.posix_shm_sockets.shared_params import MSG_SIZE

# Create an int encoder to allow encoding length
int_struct = struct.Struct('i')

# Clean up since last time
try: posix_ipc.unlink_shared_memory('server_queue')
except: pass
try: posix_ipc.unlink_semaphore('server_queue')
except: pass

# Create the shared memory and the semaphore,
# and map it with mmap
memory = posix_ipc.SharedMemory(
    'server_queue',
    posix_ipc.O_CREX,
    size=MSG_SIZE
)
semaphore = posix_ipc.Semaphore(
    'server_queue',
    posix_ipc.O_CREX
)
mapfile = mmap.mmap(memory.fd, memory.size)
memory.close_fd()
semaphore.release()

while 1:
    semaphore.acquire()
    msg = b"MY VERY LONG TEST MESSAGE!"
    mapfile[0:int_struct.size] = int_struct.pack(len(msg))
    mapfile[int_struct.size:int_struct.size+len(msg)] = msg
    semaphore.release()

    break

# Clean up
mapfile.close()
posix_ipc.unlink_shared_memory('server_queue')
semaphore.unlink()
