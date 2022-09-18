import sys
import time
import psutil
import signal
import _thread
import importlib
from sys import argv
from os import getpid
from typing import Iterator, Tuple

from speedysvc.Service import Service
from speedysvc.toolkit.io.make_dirs import make_dirs
from speedysvc.web_monitor.app import web_service_manager
from speedysvc.toolkit.py_ini.read.ReadIni import ReadIni
from speedysvc.logger.std_logging.FIFOJSONLog import FIFOJSONLog
from speedysvc.client_server.base_classes.ServerProviderBase import ServerProviderBase


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

    def wait_to_exit(service):
        try:
            print("Main service waiting for PID to exit:", service.get_pid())
            service.stop()
        finally:
            waiting_num[0] -= 1

    for services in _ALL_INSTS:
        for service_name, service in services.iter_services_by_name():
            waiting_num[0] += 1
            _thread.start_new_thread(wait_to_exit, (service,))

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


def _convert_values(values):
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
        'service_port': greater_than_0_int,
        'service_name': lambda x: x,
        'log_dir': lambda x: x,
        'host': lambda x: x,
        'server_module': lambda x: x,
        'import_from': lambda x: x,
        'client_module': lambda x: x,
        'tcp_allow_insecure_serialisation': convert_bool,
        'max_proc_num': greater_than_0_int,
        'min_proc_num': greater_than_0_int,
        'max_proc_mem_bytes': greater_than_0_int_or_none,
        'wait_until_completed': convert_bool
    }
    return {k: arg_keys[k](v) for k, v in values.items()}


_ALL_INSTS = []


class Services:
    def __init__(self):
        _ALL_INSTS.append(self)

        self.services = {}
        self.services_by_port = {}
        self.values_dict = ReadIni().read_D(argv[-1])

        self.web_monitor_dict = self.values_dict.pop('web monitor') \
            if 'web monitor' in self.values_dict else {}

        if 'defaults' in self.values_dict:
            defaults_dict = self.values_dict.pop('defaults')
            self.defaults_dict = defaults_dict = _convert_values(defaults_dict)
        else:
            self.defaults_dict = defaults_dict = {}

        if 'log_dir' not in defaults_dict:
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

    def iter_services_by_name(self) -> Iterator[Tuple[str, ServerProviderBase]]:
        for service in sorted(self.services, key=lambda i: i.lower()):
            yield service, self.services[service]

    #====================================================================#
    #                          Start Services                            #
    #====================================================================#

    def start_all_services(self):
        for service_class_name in self.values_dict.keys():
            # Note that values_dict is an OrderedDict, which means services
            # are created in the order they're defined in the .ini file.
            self.start_service_by_class_name(service_class_name)

    def start_service_by_class_name(self, service_class_name):
        section_dict = self.values_dict[service_class_name].copy()
        args_dict = self.defaults_dict.copy()
        args_dict.update(_convert_values(section_dict))
        args_dict['service_class_name'], args_dict['server_module'] = service_class_name.split(':')

        if args_dict['service_name'] not in self.services:
            s = Service(**args_dict)
            self.services[args_dict['service_name']] = s
            self.services_by_port[args_dict['service_port']] = s

        self.services[args_dict['service_name']].start()
        return self.services[args_dict['service_name']]

