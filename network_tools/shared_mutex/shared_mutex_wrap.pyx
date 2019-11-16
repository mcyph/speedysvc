cimport cython
cimport shared_mutex_wrap
from posix.time cimport clock_gettime, timespec, CLOCK_REALTIME


def cleanup(char* mutex_loc):
    # Cleans up the mutex only if need be
    shared_mutex_wrap.printf("Destroying %s\n", mutex_loc)
    cdef shared_mutex_wrap.shared_mutex_t _cu_mutex
    _cu_mutex = shared_mutex_wrap.shared_mutex_init(mutex_loc, 0777)
    if _cu_mutex.ptr != NULL:
        return shared_mutex_destroy(_cu_mutex)
    return 0


cdef char LOCKED = 1;
cdef char UNLOCKED = 0;


@cython.final
cdef class SharedMutex:
    cdef shared_mutex_wrap.shared_mutex_t _mutex
    cdef int _cleaned_up

    def __cinit__(self, char* mutex_loc):
        # "/my-mutex"
        self._cleaned_up = 1
        self._mutex = shared_mutex_wrap.shared_mutex_init(mutex_loc, 0777)
        if self._mutex.ptr == NULL:
            shared_mutex_wrap.printf("An error occurred initialising mutex %s\n", mutex_loc)
            return
        if self._mutex.created:
            shared_mutex_wrap.printf("The mutex %s was just created\n", mutex_loc)
        else:
            shared_mutex_wrap.printf("The mutex %s was NOT just created\n", mutex_loc)
        self._cleaned_up = 0

    def __del__(self):
        if not self._cleaned_up:
            self.close()
    
    cpdef int close(self) nogil:
        # Closing is used to release local resources, used by a mutex.
        # It's still available to any other process.
        self._cleaned_up = 1
        if shared_mutex_wrap.shared_mutex_close(self._mutex):
            return 1
        return 0
    
    cpdef int cleanup(self) nogil:
        # Mutex destruction completely cleans it from system memory.
        self._cleaned_up = 1
        if shared_mutex_wrap.shared_mutex_destroy(self._mutex):
            return 1
        return 0

    cpdef int lock(self) nogil:
        # Use pthread calls for locking and unlocking.
        cdef int i
        cdef int retval;
        cdef double from_t = self.get_current_time()

        with nogil:
            while 1:
            #for i from 0 <= i < 999999999 by 1:
                # The Linux kernel time slice is normally around 6ms max
                # (minimum 0.5ms) so doesn't (necessarily?) make sense to
                # consume more time busy waiting
                if self.get_current_time()-from_t > 1:
                    break
                elif self._mutex.spin_lock_char[0] == UNLOCKED:
                    break

            retval = shared_mutex_wrap.pthread_mutex_lock(self._mutex.ptr)
            self._mutex.spin_lock_char[0] = LOCKED
            return retval

    cdef double get_current_time(self) nogil:
        cdef timespec ts
        cdef double current
        clock_gettime(CLOCK_REALTIME, &ts)
        current = ts.tv_sec + (ts.tv_nsec / 1000000000.)
        return current
        
    cpdef int unlock(self) nogil:
        cdef int i
        cdef int retval;

        with nogil:
            self._mutex.spin_lock_char[0] = UNLOCKED
            retval = shared_mutex_wrap.pthread_mutex_unlock(self._mutex.ptr)
            return retval
