cimport shared_mutex_wrap


cdef class SharedMutex:
    cdef shared_mutex_wrap.shared_mutex_t _mutex

    def __cinit__(self, char* mutex_loc):
        # "/my-mutex"
        self._mutex = shared_mutex_wrap.shared_mutex_init(mutex_loc, 0777)
        if self._mutex.ptr == NULL:
            shared_mutex_wrap.printf("An error occurred initialising mutex\n")
        if self._mutex.created:
            shared_mutex_wrap.printf("The mutex was just created\n")
    
    def close(self):
        # Closing is used to release local resources, used by a mutex.
        # It's still available to any other process.
        if shared_mutex_wrap.shared_mutex_close(self._mutex):
            return 1
        return 0
    
    def cleanup(self):
        # Mutex destruction completely cleans it from system memory.
        if shared_mutex_wrap.shared_mutex_destroy(self._mutex):
            return 1
        return 0

    def lock(self):
        # Use pthread calls for locking and unlocking.
        shared_mutex_wrap.pthread_mutex_lock(self._mutex.ptr)
        
    def unlock(self):
        shared_mutex_wrap.pthread_mutex_unlock(self._mutex.ptr)

