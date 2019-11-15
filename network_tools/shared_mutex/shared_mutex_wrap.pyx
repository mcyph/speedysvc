cimport cython
cimport shared_mutex_wrap


def cleanup(char* mutex_loc):
    # Cleans up the mutex only if need be
    shared_mutex_wrap.printf("Destroying %s\n", mutex_loc)
    cdef shared_mutex_wrap.shared_mutex_t _cu_mutex
    _cu_mutex = shared_mutex_wrap.shared_mutex_init(mutex_loc, 0777)
    if _cu_mutex.ptr != NULL:
        return shared_mutex_destroy(_cu_mutex)
    return 0


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
        with nogil:
            self._cleaned_up = 1
            if shared_mutex_wrap.shared_mutex_close(self._mutex):
                return 1
            return 0
    
    cpdef int cleanup(self) nogil:
        # Mutex destruction completely cleans it from system memory.
        with nogil:
            self._cleaned_up = 1
            if shared_mutex_wrap.shared_mutex_destroy(self._mutex):
                return 1
            return 0

    cpdef int lock(self) nogil:
        # Use pthread calls for locking and unlocking.
        with nogil:
            return shared_mutex_wrap.pthread_mutex_lock(self._mutex.ptr)
        
    cpdef int unlock(self) nogil:
        with nogil:
            return shared_mutex_wrap.pthread_mutex_unlock(self._mutex.ptr)
