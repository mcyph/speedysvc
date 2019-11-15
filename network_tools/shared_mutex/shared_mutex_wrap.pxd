from posix.types cimport (blkcnt_t, blksize_t, dev_t, gid_t, ino_t, mode_t,
                          nlink_t, off_t, time_t, uid_t)
from libc.stdio cimport printf
from posix.mman cimport (shm_open, shm_unlink, mmap, munmap,
                         PROT_READ, PROT_WRITE, MAP_SHARED, MAP_FAILED)


cdef extern from "<pthread.h>" nogil:
    # https://github.com/python-llfuse/python-llfuse/blob/master/Include/pthread.pxd    
    # POSIX says this might be a struct, but CPython (and llfuse)
    # rely on it being an integer.
    ctypedef int pthread_t

    ctypedef struct pthread_attr_t:
        pass
    ctypedef struct pthread_mutexattr_t:
        pass
    ctypedef struct pthread_mutex_t:
       pass

    enum:
        PTHREAD_CANCEL_ENABLE
        PTHREAD_CANCEL_DISABLE

    int pthread_cancel(pthread_t thread)
    int pthread_setcancelstate(int state, int *oldstate)
    pthread_t pthread_self()
    #int pthread_sigmask(int how, sigset_t *set, sigset_t *oldset)
    int pthread_equal(pthread_t t1, pthread_t t2)
    int pthread_create(pthread_t *thread, pthread_attr_t *attr,
                       void *(*start_routine) (void *), void *arg)
    int pthread_join(pthread_t thread, void **retval)
    int pthread_kill(pthread_t thread, int sig)

    int pthread_mutex_init(pthread_mutex_t *mutex, pthread_mutexattr_t *mutexattr)
    int pthread_mutex_lock(pthread_mutex_t *mutex)
    int pthread_mutex_unlock(pthread_mutex_t *mutex)
    

cdef extern from "shared_mutex.h" nogil:
    # Structure of a shared mutex.
    ctypedef struct shared_mutex_t:
        pthread_mutex_t *ptr
        int shm_fd
        char* name
        int created

    shared_mutex_t shared_mutex_init(const char *name, mode_t mode)
    int shared_mutex_close(shared_mutex_t mutex)
    int shared_mutex_destroy(shared_mutex_t mutex)
