from HybridLock import HybridLock, CONNECT_OR_CREATE, CONNECT_TO_EXISTING


if __name__ == '__main__':
    lock = HybridLock(b"my semaphore", CONNECT_OR_CREATE)
    lock.lock()

    try:
        lock.lock(1)
    except TimeoutError:
        pass

    lock2 = HybridLock(b"my semaphore", CONNECT_TO_EXISTING)

    #lock2.lock()
    #print("SHOULDN'T GET HERE!")

    lock.unlock()
    lock.lock()
    lock.unlock()
    lock.lock(1)
    #lock.lock(1)
