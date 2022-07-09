import os
import sys
import json
import time
import signal
import psutil
import _thread
import importlib
import subprocess
from sys import argv
from os import getpid
from multiprocessing import cpu_count

from speedysvc.toolkit.io.make_dirs import make_dirs
from speedysvc.toolkit.py_ini.read.ReadIni import ReadIni
from speedysvc.logger.std_logging.FIFOJSONLog import FIFOJSONLog
from speedysvc.kill_pid_and_children import kill_pid_and_children
from speedysvc.logger.std_logging.LoggerServer import LoggerServer
from speedysvc.web_monitor.app import web_service_manager, run_server  # TODO: Decouple from this?


_handling_sigint = [False]


def signal_handler(sig, frame):
    """
    SIGINT received, likely due to ctrl+c
    try to exit as cleanly as possible,
    recursively exiting child processes
    """
    if _handling_sigint[0]:
        return
    _handling_sigint[0] = True

    waiting_num = [0]

    def wait_to_exit(proc):
        try:
            print("Main service waiting for PID to exit:", proc.pid)
            kill_pid_and_children(proc.pid)
        finally:
            waiting_num[0] -= 1

    for _proc in services.DProcByName.values():
        waiting_num[0] += 1
        _thread.start_new_thread(wait_to_exit, (_proc,))

    while waiting_num[0]:
        time.sleep(0.01)

    # Windows in particular needs to be more
    # forcibly shut down for some reason
    me = psutil.Process(getpid())
    me.terminate()
    try:
        me.kill()
    except psutil.NoSuchProcess:
        pass

    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def __convert_values(values):
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

    def greater_than_0_int_or_none(i):
        if i is None:
            return i
        i = int(i)
        assert i > 0, "Value should be greater than 0"
        return i

    arg_keys = {
        'port': greater_than_0_int,
        'service_name': lambda x: x,
        'log_dir': lambda x: x,
        'host': lambda x: x,
        'tcp_allow_insecure_serialisation': convert_bool,
        'max_proc_num': greater_than_0_int,
        'min_proc_num': greater_than_0_int,
        'max_proc_mem_bytes': greater_than_0_int_or_none,
        'wait_until_completed': convert_bool
    }
    return {k: arg_keys[k](v) for k, v in values.items()}


class Services:
    def __init__(self):
        self.services = {}
        self.services_by_port = {}
        self.DValues = ReadIni().read_D(argv[-1])

        self.DWebMonitor = self.DValues.pop('web monitor') \
            if 'web monitor' in self.DValues else {}

        if 'defaults' in self.DValues:
            defaults_dict = self.DValues.pop('defaults')
            self.defaults_dict = defaults_dict = __convert_values(defaults_dict)
        else:
            self.defaults_dict = defaults_dict = {}

        if not 'log_dir' in defaults_dict:
            # Note this - the logger parent always uses the "default" dir currently
            defaults_dict['log_dir'] = '/tmp/shmrpc_logs'

        # Create the "parent logger" for all processes
        make_dirs(defaults_dict['log_dir'])
        self.fifo_json_log_parent = FIFOJSONLog(f"{defaults_dict['log_dir']}/global_log.json")
        web_service_manager.set_logger_parent(self.fifo_json_log_parent)

        # Start all services, as defined in the .ini file
        # TODO: Allow starting only some services using the commandline?
        self.start_all_services()

    def get_service_by_port(self, port: int) -> Service:
        return self.services_by_port[port]

    def get_service_by_name(self, service_name: str) -> Service:
        return self.services[service_name]

    def iter_services_by_name(self):
        for service in sorted(self.services, key=lambda service: service.lower()):
            yield service, self.services[service]

    #====================================================================#
    #                          Start Services                            #
    #====================================================================#

    def start_all_services(self):
        for service_class_name in self.services.keys():
            # Note that DValues is an OrderedDict, which means services
            # are created in the order they're defined in the .ini file.
            self.start_service(service_class_name)

    def start_service_by_name(self, service_class_name):
        section_dict = self.DValues[service_class_name].copy()
        args_dict = self.defaults_dict.copy()
        args_dict.update({k: self.DArgKeys[k](v) for k, v in section_dict.items()})

        import_from = section_dict.pop('import_from')
        server_methods = getattr(importlib.import_module(import_from), service_class_name)
        s = Service(server_methods, **args_dict)
        self.services[service_name] = s
        self.services_by_port[port] = s
        return s

