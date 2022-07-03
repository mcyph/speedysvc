import psutil
from psutil import pid_exists


def is_pid_still_alive(pid: int):
    if not pid_exists(pid):
        return False

    try:
        proc = psutil.Process(pid=pid)
        if proc.status() == psutil.STATUS_ZOMBIE:
            return False
    except:
        import traceback
        traceback.print_exc()
        return False

    return True
