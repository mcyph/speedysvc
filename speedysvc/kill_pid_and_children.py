import os
import sys
import time
import errno
import psutil
import signal
from typing import Optional


def debug(*s):
    if False:
        print(*s)


def wait_for_pid(pid: int,
                 timeout: Optional[int] = None):

    elapsed = 0

    while True:
        if timeout and elapsed >= timeout:
            raise TimeoutError()

        try:
            _pid, err_code = os.waitpid(pid, os.WNOHANG)

            if err_code == errno.ECHILD:
                # Child should no longer exist?
                # but it seems it often still does, hence this additional check
                # Is there an alternative to this?
                if not psutil.pid_exists(pid):
                    break
            elif not err_code:
                # the return values from waitpid are unreliable,
                # so will use pid_exists instead
                if not psutil.pid_exists(pid):
                    break
        except ChildProcessError:
            if not psutil.pid_exists(pid):
                break  # Ditto

        time.sleep(0.01)
        elapsed += 0.01


def kill_pid_and_children(pid: int,
                          sigint_timeout: int = 5,
                          sigterm_timeout: int = 5):

    # Send a SIGINT to the process, and all child processes
    current_process = psutil.Process(pid)
    LKillPIDs = (
        list([i.pid for i in current_process.children(recursive=True)]) +
        [pid]
    )
    for pid in LKillPIDs:
        debug(f"Sending SIGINT to pid: [{pid}]")
        try:
            os.kill(pid, signal.SIGINT)
        except ProcessLookupError:
            continue

    for pid in LKillPIDs:
        try:
            process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            continue

        try:
            if sys.platform != 'win32':
                debug(f"Waiting for PID: [{pid}]")
                wait_for_pid(pid, timeout=sigint_timeout)
            else:
                time.sleep(0.5)
        except TimeoutError:
            # If that fails, send SIGTERM
            debug(f"Sending SIGTERM to pid: [{pid}]")
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                sigint_timeout = 0.01
                continue
            sigint_timeout = 0.01

            try:
                if sys.platform != 'win32':
                    wait_for_pid(pid, timeout=sigterm_timeout)
                else:
                    pass
            except TimeoutError:
                # Send SIGKILLs if all else fails
                debug(f"Sending SIGKILL to pid: [{pid}]")
                try:
                    process.kill()
                except psutil.NoSuchProcess:
                    sigterm_timeout = 0.01
                    continue
                sigterm_timeout = 0.01

