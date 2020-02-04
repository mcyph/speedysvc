from posix.types cimport mode_t
from posix.time cimport timespec


cdef extern from "<semaphore.h>" nogil:
    ctypedef struct sem_t:
        pass

    #int sem_init(sem_t *sem, int pshared, unsigned int value)

    sem_t *sem_open(const char *name, int oflag,
                    mode_t mode, unsigned int value)
    #sem_t *sem_open(const char *name, int oflag)
    int sem_post(sem_t *sem)
    int sem_wait(sem_t *sem)
    int sem_timedwait(sem_t *sem, const timespec *abs_timeout)
    int sem_close(sem_t *sem)
    int sem_destroy(sem_t *mutex)
    int sem_unlink(const char *name)
    int sem_getvalue(sem_t *sem, int *value)
