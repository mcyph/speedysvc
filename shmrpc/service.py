import os
import json
import time
import _thread
import subprocess
from multiprocessing import cpu_count

from shmrpc.logger.std_logging.LoggerServer import LoggerServer
from shmrpc.logger.std_logging.FIFOJSONLog import FIFOJSONLog
from shmrpc.toolkit.io.make_dirs import make_dirs
from shmrpc.toolkit.py_ini.read.ReadIni import ReadIni
from shmrpc.web_monitor.app import web_service_manager, run_server


# A variable to make sure the servers stay
# persistent, and won't be garbage-collected
__LServers = []
__LLoggerServers = []


def run_multi_proc_server(server_methods, import_from, section,
                          log_dir='/tmp',
                          tcp_bind=None,
                          tcp_compression=None,
                          tcp_allow_insecure_serialisation=False,

                          max_proc_num=cpu_count(),
                          min_proc_num=1,
                          wait_until_completed=True,

                          fifo_json_log_parent=None):

    print(f"{server_methods.name} parent: starting service")
    make_dirs(f"{log_dir}/{server_methods.name}")
    logger_server = LoggerServer(
        log_dir=f'{log_dir}/{server_methods.name}/',
        server_methods=server_methods,
        fifo_json_log_parent=fifo_json_log_parent
    )
    __LLoggerServers.append(logger_server)

    DEnv = os.environ.copy()
    DEnv["PATH"] = "/usr/sbin:/sbin:" + DEnv["PATH"]
    DArgs = {
        'import_from': import_from,
        'section': section,
        'tcp_bind': tcp_bind,
        'tcp_compression': tcp_compression,
        'tcp_allow_insecure_serialisation': tcp_allow_insecure_serialisation,

        'min_proc_num': min_proc_num,
        'max_proc_num': max_proc_num,
        'max_proc_mem_bytes': None,

        'new_proc_cpu_pc': 0.3,
        'new_proc_avg_over_secs': 20,
        'kill_proc_avg_over_secs': 240,

        'wait_until_completed': wait_until_completed
    }
    proc = subprocess.Popen([
        'python3', '-m',
        'shmrpc.service_managers.multi_process_manager.MultiProcessManager',
        json.dumps(DArgs)
    ], env=DEnv)
    __LServers.append(proc)

    logger_server.proc = proc # HACK!
    web_service_manager.add_service(logger_server)

    if wait_until_completed:
        while logger_server.get_service_status() != 'started':
            time.sleep(0.1)


if __name__ == '__main__':
    import importlib
    from sys import argv
    DValues = ReadIni().read_D(argv[-1])

    def convert_bool(i):
        return {
            'true': True,
            'false': False,
            '0': False,
            '1': True
        }[i.lower()]

    def greater_than_0_int(i):
        i = int(i)
        assert i > 0, "Value should be greater than 0"
        return i

    DArgKeys = {
        'log_dir': lambda x: x,
        'tcp_bind': lambda x : x,
        'tcp_compression': lambda x: x,
        'tcp_allow_insecure_serialisation': convert_bool,
        'max_proc_num': greater_than_0_int,
        'min_proc_num': greater_than_0_int,
        'wait_until_completed': convert_bool
    }

    if 'defaults' in DValues:
        DDefaults = DValues.pop('defaults')
        DDefaults = {k: DArgKeys[k](v) for k, v in DDefaults.items()}
    else:
        DDefaults = {}

    if not 'log_dir' in DDefaults:
        # Note this - the logger parent always uses the "default" dir currently
        DDefaults['log_dir'] = '/tmp/shmrpc_logs'

    make_dirs(DDefaults['log_dir'])
    fifo_json_log_parent = FIFOJSONLog(f"{DDefaults['log_dir']}/global_log.json")
    web_service_manager.set_logger_parent(fifo_json_log_parent)

    try:
        for section, DSection in DValues.items():
            #print("SECTION:", section)
            import_from = DSection.pop('import_from')
            server_methods = getattr(importlib.import_module(import_from), section) # Package?

            DArgs = DDefaults.copy()
            DArgs.update({k: DArgKeys[k](v) for k, v in DSection.items()})
            run_multi_proc_server(
                server_methods, import_from, section,
                **DArgs,
                fifo_json_log_parent=fifo_json_log_parent
            )

        print("Services started - starting web monitoring interface")

        # OPEN ISSUE: Allow binding to a specific address here? ====================================
        # For security reasons, it's probably (in almost all cases)
        # better to only allow on localhost, to prevent other people
        # stopping services, etc

        # Note opening the web server from a different thread -
        # this allows intercepting ctrl+c/SIGINT
        # It may be that SIGINT is handled in the actual webserver code,
        # but I want to make sure child processes clean up when SIGINT is called.
        _thread.start_new_thread(run_server, (), {'debug': False})
        while 1:
            time.sleep(10)
    except:
        import traceback
        traceback.print_exc()

        for proc in __LServers:
            print("Main service waiting for PID to exit:", proc.pid)
            try:
                proc.wait(15)
            except subprocess.TimeoutExpired:
                import signal
                #os.kill(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    os.kill(proc.pid, signal.SIGKILL)
            try:
                os.waitpid(proc.pid, 0)
            except ChildProcessError:
                pass
        raise
