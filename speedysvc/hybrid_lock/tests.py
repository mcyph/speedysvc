from hybrid_lock import HybridLock, \
    CONNECT_OR_CREATE, \
    CONNECT_TO_EXISTING, \
    CREATE_NEW_OVERWRITE, \
    CREATE_NEW_EXCLUSIVE, \
    SemaphoreExistsException, \
    NoSuchSemaphoreException


def test1():
    # First try to create, overwriting+destroying
    print("Creating new overwrite!")
    created = HybridLock(b'test', CREATE_NEW_OVERWRITE)
    created = HybridLock(b'test', CREATE_NEW_OVERWRITE)
    print(created.get_value())
    created.destroy()
    del created


def test2():
    # Then try to create exclusive, making sure
    # successive exclusive requests don't work
    exclusive = HybridLock(b'test', CREATE_NEW_EXCLUSIVE)
    try:
        HybridLock(b'test', CREATE_NEW_EXCLUSIVE)
        raise Exception("Shouldn't get here")
    except SemaphoreExistsException:
        pass
    except:
        raise

    # Then try to connect to an existing one
    existing = HybridLock(b'test', CONNECT_TO_EXISTING)
    existing_2 = HybridLock(b'test', CONNECT_OR_CREATE)

    # Make sure locking/unlocking one does the same to the other
    assert existing.get_value() == \
           existing_2.get_value() == \
           exclusive.get_value() == 1, (existing.get_value(), exclusive.get_value())
    exclusive.lock()
    assert existing.get_value() == \
           existing_2.get_value() == \
           exclusive.get_value() == 0, (existing.get_value(), exclusive.get_value())
    exclusive.unlock()

    # Try destroying one, and make sure every one is invalidated
    existing.destroy()
    assert exclusive.get_destroyed() and \
           existing.get_destroyed() and \
           existing_2.get_destroyed()

    # Make sure we can't connect to it
    try:
        HybridLock(b'test', CONNECT_TO_EXISTING)
        raise Exception("Shouldn't get here!")
    except NoSuchSemaphoreException:
        pass

def test3():
    # Try killing one process, then reconnecting to the server
    created = HybridLock(b'test', CREATE_NEW_OVERWRITE)


test1()
test2()
