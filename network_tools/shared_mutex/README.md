# shared_mutex

Microlibrary for inter-process mutexes on Linux.

## Example which says it all

```c
#include "shared_mutex.h"
#include <stdio.h>

int main() {
  // Init shared mutex by a name, which can be used by
  // any other process to access the mutex.
  // This function both creates new and opens an existing mutex.
  shared_mutex_t mutex = shared_mutex_init("/my-mutex");
  if (mutex.ptr == NULL) {
    return 1;
  }

  if (mutex.created) {
    printf("The mutex was just created\n");
  }

  // Use pthread calls for locking and unlocking.
  pthread_mutex_lock(mutex.ptr);
  printf("Press eny key to unlock the mutex");
  getchar();
  pthread_mutex_unlock(mutex.ptr);

  // Closing is used to release local resources, used by a mutex.
  // It's still available to any other process.
  if (shared_mutex_close(mutex)) {
    return 1;
  }
  return 0;
}

int cleanup() {
  // Mutex destruction completely cleans it from system memory.
  if (shared_mutex_destroy(mutex)) {
    return 1;
  }
  return 0;
}
```

## Usage

* Download `shared_mutex.h` and `shared_mutex.c` into your project.
* Building requires linking with `pthread` and `librt`.

## Docs

### shared_mutex_t

Structure of a shared mutex.
```c
typedef struct shared_mutex_t {
  pthread_mutex_t *ptr; // Pointer to the pthread mutex and
                        // shared memory segment.
  int shm_fd;           // Descriptor of shared memory object.
  char* name;           // Name of the mutex and associated
                        // shared memory object.
  int created;          // Equals 1 (true) if initialization
                        // of this structure caused creation
                        // of a new shared mutex.
                        // Equals 0 (false) if this mutex was
                        // just retrieved from shared memory.
} shared_mutex_t;
```

### shared_mutex_init

```c
shared_mutex_t shared_mutex_init(char *name);
```

Initialize a new shared mutex with given `name`. If a mutex with such name exists in the system, it will be loaded. Otherwise a new mutes will by created.

In case of any error, it will be printed into the standard output and the returned structure will have `ptr` equal `NULL`. `errno` wil not be reset in such case, so you may used it.

**NOTE:** In case when the mutex appears to be uncreated, this function becomes *non-thread-safe*. If multiple threads call it at one moment, there occur several race conditions, in which one call might recreate another's shared memory object or rewrite another's pthread mutex in the shared memory. There is no workaround currently, except to run first initialization only before multi-threaded or multi-process functionality.

### shared_mutex_close

```c
int shared_mutex_close(shared_mutex_t mutex);
```

Close access to the shared mutex and free all the resources, used by the structure.

Returns 0 in case of success. If any error occurs, it will be printed into the standard output and the function will return -1. `errno` wil not be reset in such case, so you may used it.

**NOTE:** It will not destroy the mutex. The mutex would not only be available to other processes using it right now, but also to any process which might want to use it later on. For complete desctruction use `shared_mutex_destroy` instead.

**NOTE:** It will not unlock locked mutex.

### shared_mutex_destroy

```c
int shared_mutex_destroy(shared_mutex_t mutex);
```

Close and destroy shared mutex. Any open pointers to it will be invalidated. 

Returns 0 in case of success. If any error occurs, it will be printed into the standard output and the function will return -1. `errno` wil not be reset in such case, so you may used it.

**NOTE:** It will not unlock locked mutex.
