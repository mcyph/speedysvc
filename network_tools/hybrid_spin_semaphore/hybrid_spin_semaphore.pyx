cimport cython
cimport hybrid_spin_semaphore

from libc.errno cimport ENOENT, errno
from libc.stdio cimport printf, perror

from posix.stat cimport fchmod
from posix.unistd cimport ftruncate, close
from posix.fcntl cimport O_CREAT, O_EXCL, O_RDWR
from posix.time cimport clock_gettime, timespec, CLOCK_REALTIME
from posix.mman cimport (PROT_READ, PROT_WRITE, MAP_SHARED, MAP_FAILED)
from posix.mman cimport mmap, shm_open


def destroy(char* sem_loc):
    # TODO: Add error handling!
    # NOTE: Destroying semaphores created by other processes
    # can produce undefined behaviour..although I'm willing
    # to take that risk here, as if we're starting a new server
    # process I probably want to take over from the last one.
    return sem_unlink(sem_loc)


cdef char UNLOCKED = 0
cdef char LOCKED = 1
cdef char DESTROYED = 2


@cython.final
cdef class HybridSpinSemaphore:
    cdef sem_t* _semaphore
    cdef int _cleaned_up
    cdef char* _spin_lock_char
    cdef int _shm_fd
    cdef char* _sem_loc

    #===========================================================#
    #                  Init Semaphore/Spinlock                  #
    #===========================================================#

    def __cinit__(self,
                  char* sem_loc,
                  int create_new=1,
                  int initial_value=1,
                  int destroy_on_process_exit=1):

        self._cleaned_up = 1
        self._sem_loc = sem_loc

        # Initialise shared memory for the "spin lock" char
        # (which allows basic busy waiting)
        self.init_mmap(sem_loc)

        # Initialize semaphores for shared processes
        # First try to connect to a previously created semaphore
        self._semaphore = sem_open(sem_loc, O_RDWR, 0666, initial_value) # WARNING!!!

        if self._semaphore == NULL:
            # One didn't exist: create one in shared mode
            self._semaphore = sem_open(
                sem_loc, O_CREAT | O_EXCL,
                0666, initial_value
            )
        self._cleaned_up = 0

    cdef int init_mmap(self, char* sem_loc) except -1:
        # Open existing shared memory object, or create one.
        # Two separate calls are needed here, to mark fact of creation
        # for later initialization of pthread mutex.
        self._shm_fd = shm_open(sem_loc, O_RDWR, 0666)

        if errno == ENOENT:
            # Need to create a new shared memory item
            self._shm_fd = shm_open(sem_loc, O_RDWR|O_CREAT, 0666)

            # Change permissions of shared memory, so every
            # body can access it. Avoiding the umask of shm_open
            if fchmod(self._shm_fd, 0666) != 0:
                perror("fchmod")
                return -1

        if self._shm_fd == -1:
            perror("shm_open")
            return -1

        # Truncate shared memory segment so it would contain char*
        if ftruncate(self._shm_fd, sizeof(char*)) != 0:
            perror("ftruncate")
            return -1

        # Map pthread mutex into the shared memory.
        cdef void *addr = mmap(
            NULL,
            sizeof(char*),
            PROT_READ|PROT_WRITE,
            MAP_SHARED,
            self._shm_fd,
            0
        )
        if addr == MAP_FAILED:
            perror("mmap")
            return -1

        self._spin_lock_char = <char *>addr # VOLATILE??? ===========================================
        return 0

    #===========================================================#
    #                      Destroy/Close                        #
    #===========================================================#

    def __del__(self):
        if not self._cleaned_up:
            # Closing is used to release local resources, used by a mutex.
            # It's still available to any other process.
            self._cleaned_up = 1

            if close(self._shm_fd):
                perror("close")
                raise Exception(
                    "Error closing shared memory file descriptor"
                )
            return sem_close(self._semaphore)

    cpdef int destroy(self) nogil except -1:
        # Mutex destruction completely cleans it from system memory.
        if self._cleaned_up:
            raise Exception(
                "destroy called on semaphore that no longer exists"
            )
            return -1
        self._cleaned_up = 1

        if close(self._shm_fd):
            perror("close")
            return -1

        # after calling sem_unlink, if there are no more
        # processes using it, it will cease to exist.
        if sem_unlink(self._sem_loc) == -1:
            return -1
        return sem_close(self._semaphore)

    #===========================================================#
    #                    Get Semaphore Value                    #
    #===========================================================#

    cpdef int get_value(self) nogil except -10:
        cdef int value;
        cdef int* p_value = &value;
        cdef int result = sem_getvalue(self._semaphore, p_value)
        if result == -1:
            return -10
        return p_value[0]

    #===========================================================#
    #                        Lock/Unlock                        #
    #===========================================================#

    cpdef int lock(self) nogil except -1:
        # Use pthread calls for locking and unlocking.
        cdef int i
        cdef int retval
        cdef double from_t = self.get_current_time()

        with nogil:
            while 1:
                # The Linux kernel time slice is normally around 6ms max
                # (minimum 0.5ms) so doesn't (necessarily?) make sense to
                # consume more time busy waiting
                if self.get_current_time()-from_t > 1:
                    break
                elif self._spin_lock_char[0] == UNLOCKED:
                    break

            retval = sem_wait(self._semaphore)
            self._spin_lock_char[0] = LOCKED
            return retval

    cpdef int unlock(self) nogil except -1:
        cdef int i
        cdef int retval

        with nogil:
            self._spin_lock_char[0] = UNLOCKED
            retval = sem_post(self._semaphore)
            return retval

    #===========================================================#
    #                       Miscellaneous                       #
    #===========================================================#

    cdef double get_current_time(self) nogil:
        cdef timespec ts
        cdef double current
        clock_gettime(CLOCK_REALTIME, &ts)
        current = ts.tv_sec + (ts.tv_nsec / 1000000000.)
        return current
