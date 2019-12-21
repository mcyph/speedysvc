# https://gist.github.com/sirkonst/5bfd26f7f07c692441be76dc6c973cb4
import ctypes
import threading
import time


# inspired by https://github.com/mosquito/crew/blob/master/crew/worker/thread.py
def kill_thread(
        thread: threading.Thread,
        exception: BaseException=KeyboardInterrupt
) -> None:
    if not thread.isAlive():
        return

    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), ctypes.py_object(exception)
    )

    if res == 0:
        raise ValueError('nonexistent thread id')
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError('PyThreadState_SetAsyncExc failed')

    while thread.isAlive():
        time.sleep(0.01)
