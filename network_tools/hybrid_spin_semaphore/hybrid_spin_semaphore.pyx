cimport cython
cimport hybrid_spin_semaphore

from libc.errno cimport ENOENT, errno
from libc.stdio cimport printf, perror

from posix.stat cimport fchmod
from posix.unistd cimport ftruncate, close
from posix.fcntl cimport O_CREAT, O_EXCL, O_RDWR
from posix.time cimport clock_gettime, timespec, CLOCK_REALTIME
from posix.mman cimport PROT_READ, PROT_WRITE, MAP_SHARED, MAP_FAILED
from posix.mman cimport mmap, shm_open, shm_unlink


class SemaphoreExistsException(Exception):
    pass

class NoSuchSemaphoreException(Exception):
    pass


CONNECT_OR_CREATE = 0
CONNECT_TO_EXISTING = 1
CREATE_NEW_OVERWRITE = 2
CREATE_NEW_EXCLUSIVE = 3


cdef char LOCKED = 0
cdef char UNLOCKED = 1
# Just to make sure we can't ever have trouble with
# incrementing semaphores beyond 1 (which should never happen!)
# TODO: Add checks to make sure of this!!! =================================================
cdef char DESTROYED = 127


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
                  char* sem_loc, int mode,
                  int initial_value=UNLOCKED,
                  int permissions=0666):

        self._cleaned_up = 1
        self._sem_loc = sem_loc

        if mode == CONNECT_OR_CREATE:
            # Initialize semaphores for shared processes
            # First try to connect to a previously created semaphore
            self._semaphore = sem_open(
                sem_loc, O_RDWR,
                permissions, initial_value
            ) # WARNING!!!

            if self._semaphore == NULL:
                # One didn't exist: create one in shared mode
                self._semaphore = sem_open(
                    sem_loc, O_CREAT | O_EXCL,
                    0666, initial_value
                )

                # Initialise shared memory for the "spin lock" char
                # (which allows basic busy waiting)
                # Because we're creating here, we'll need to set
                # the initial value
                self.init_mmap(sem_loc, permissions, initial_value)
            else:
                # If it already exists, use the existing value
                self.init_mmap(sem_loc, permissions)

        elif mode == CONNECT_TO_EXISTING:
            # Try to open an existing semaphore,
            # raising an exception if it doesn't exist
            self._semaphore = sem_open(
                sem_loc, O_RDWR,
                permissions, initial_value
            )
            if self._semaphore == NULL:
                raise NoSuchSemaphoreException(sem_loc)

            # Connect to the existing mmap object
            self.init_mmap(sem_loc, permissions)

        elif mode == CREATE_NEW_EXCLUSIVE:
            # Open the semaphore in exclusive mode
            self._semaphore = sem_open(
                sem_loc, O_CREAT | O_EXCL,
                permissions, initial_value
            )
            if self._semaphore == NULL:
                raise SemaphoreExistsException(sem_loc)

            self.init_mmap(
                sem_loc, permissions,
                set_value=initial_value
            )

        elif mode == CREATE_NEW_OVERWRITE:
            # First, try to destroy the existing value but keep going
            # if that fails
            #
            # We need to create a new instance, so as to also set the
            # _spin_lock_char to DESTROYED and stop new processes
            # accessing the mmapped location

            try:
                existing_semaphore = HybridSpinSemaphore(
                    sem_loc, CONNECT_TO_EXISTING,
                    initial_value, permissions
                )
                existing_semaphore.destroy()
                del existing_semaphore
            except NoSuchSemaphoreException:
                pass

            # Open the semaphore in exclusive mode
            self._semaphore = sem_open(
                sem_loc, O_CREAT | O_EXCL,
                permissions, initial_value
            )
            if self._semaphore == NULL:
                # Shouldn't get here! (in normal circumstances)
                raise SemaphoreExistsException(sem_loc)

            self.init_mmap(
                sem_loc, permissions,
                set_value=initial_value
            )
        else:
            raise Exception("Unknown mode: %s" % mode)

        self._cleaned_up = 0

    cdef int init_mmap(self,
                       char* sem_loc,
                       int permissions,
                       int set_value=-1
        ) except -1:

        # Open existing shared memory object, or create one.
        # Two separate calls are needed here, to mark fact of creation
        # for later initialization of pthread mutex.
        self._shm_fd = shm_open(sem_loc, O_RDWR, permissions)

        if errno == ENOENT:
            # Need to create a new shared memory item
            self._shm_fd = shm_open(
                sem_loc, O_RDWR|O_CREAT, permissions
            )

            # Change permissions of shared memory, so every
            # body can access it. Avoiding the umask of shm_open
            if fchmod(self._shm_fd, permissions) != 0:
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

        # Create+set initial value for the spin lock char*, if provided
        self._spin_lock_char = <char *>addr # VOLATILE??? ===========================================
        if set_value != -1:
            self._spin_lock_char[0] = set_value
        return 0

    #===========================================================#
    #                      Destroy/Close                        #
    #===========================================================#

    def __del__(self):
        if not self._cleaned_up:
            # Closing is used to release local resources, used by
            # a mutex. It'll still be available to other processes
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

        # Set the spinlock char to indicate to other processes
        # that this semaphore should not be used any more
        self._spin_lock_char[0] = DESTROYED

        # After calling shm_unlink, I believe the behaviour is
        # similar to sem_unlink - that it will cease to be
        # accessible by name, but will still remain accessible
        # for processes currently using it.
        if shm_unlink(self._sem_loc) == -1:
            return -1

        # Close the shared memory
        if close(self._shm_fd):
            perror("close")
            return -1

        # after calling sem_unlink, if there are no more
        # processes using it, it will cease to exist.
        if sem_unlink(self._sem_loc) == -1:
            return -1

        # Finally close the semaphore
        return sem_close(self._semaphore)

    #===========================================================#
    #                    Get Semaphore Value                    #
    #===========================================================#

    cpdef int get_destroyed(self) nogil except -1:
        return self._spin_lock_char[0] == DESTROYED

    cpdef int get_value(self) nogil except -10:
        # Just in case the semaphore value is -1,
        # we'll use -10 for the exception
        if self._spin_lock_char[0] == DESTROYED:
            return -10

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
        if self._spin_lock_char[0] == DESTROYED:
            return -1

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
        if self._spin_lock_char[0] == DESTROYED:
            return -1

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
