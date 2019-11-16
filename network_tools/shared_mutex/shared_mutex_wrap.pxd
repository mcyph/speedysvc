from posix.types cimport (blkcnt_t, blksize_t, dev_t, gid_t, ino_t, mode_t,
                          nlink_t, off_t, time_t, uid_t)
from posix.fcntl cimport O_CREAT, O_EXCL, O_RDWR
from libc.stdio cimport printf, perror
#from posix.mman cimport (shm_open, shm_unlink, mmap, munmap,
#                         PROT_READ, PROT_WRITE, MAP_SHARED, MAP_FAILED)


cdef extern from "<semaphore.h>" nogil:
    ctypedef struct sem_t:
        pass

    #int sem_init(sem_t *sem, int pshared, unsigned int value)

    sem_t *sem_open(const char *name, int oflag,
                    mode_t mode, unsigned int value)
    #sem_t *sem_open(const char *name, int oflag)
    int sem_post(sem_t *sem)
    int sem_wait(sem_t *sem)
    int sem_close(sem_t *sem)
    int sem_destroy(sem_t *mutex)
    int sem_unlink(const char *name)
    int sem_getvalue(sem_t *sem, int *value);
