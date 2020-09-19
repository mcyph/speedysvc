import sys

if sys.platform == 'win32':
    from speedysvc.hybrid_lock.WinHybridLock import WinHybridLock as HybridLock
    from speedysvc.hybrid_lock.WinHybridLock import CONNECT_OR_CREATE, CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE, \
        CREATE_NEW_EXCLUSIVE
    from speedysvc.hybrid_lock.WinHybridLock import LOCKED, UNLOCKED, DESTROYED
    from speedysvc.hybrid_lock.WinHybridLock import SemaphoreDestroyedException, SemaphoreExistsException, \
        NoSuchSemaphoreException
else:
    from hybrid_lock import HybridLock
    from hybrid_lock import CONNECT_OR_CREATE, CONNECT_TO_EXISTING, CREATE_NEW_OVERWRITE, CREATE_NEW_EXCLUSIVE
    from hybrid_lock import LOCKED, UNLOCKED, DESTROYED
    from hybrid_lock import SemaphoreDestroyedException, SemaphoreExistsException, NoSuchSemaphoreException
