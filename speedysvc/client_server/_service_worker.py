import sys
import time
import json
import signal
import importlib
from sys import argv
from os import getpid

from speedysvc.logger.std_logging.LoggerClient import LoggerClient
from speedysvc.client_server.shared_memory.SHMServer import SHMServer
from speedysvc.client_server.network.NetworkServer import NetworkServer


def debug(*s):
    if True:
        print(*s)


def _service_worker(server_module: str,
                    service_class_name: str,
                    service_name: str,
                    service_port: int):
    """
    In child processes of MultiProcessManager
    """
    module = importlib.import_module(server_module)
    server_methods = getattr(module, service_class_name)

    debug(f"{service_name} child: Creating logger client")
    logger_client = LoggerClient(service_server_methods=server_methods,
                                 service_port=service_port,
                                 service_name=service_name)
    debug(f"{service_name} child: Creating server methods")
    smi = server_methods(logger_client)
    debug(f"{service_name} child: "
          f"Server methods created, starting implementations")

    L = []
    L.append(SHMServer(server_methods=smi,
                       service_port=service_port,
                       service_name=service_name))
    L[-1].serve_forever_in_new_thread()

    # Tell the logger server that a child has properly loaded:
    # this helps to make sure if processes are loaded properly,
    # if one depends on another.
    logger_client.set_service_status('started')

    debug(f"{service_name} worker PID [{getpid()}]: "
          f"Server methods created - listening for commands")

    _handling_sigint = [False]

    def signal_handler(sig, frame):
        if _handling_sigint[0]:
            return
        _handling_sigint[0] = True

        print(f"Intercepted keyboard interrupt for {service_name} [PID {getpid()}]")
        for inst in L:
            if hasattr(inst, 'shutdown'):
                debug(f"Calling shutdown for {service_name} [PID {getpid()}]..")
                inst.shutdown()
                debug(f"Shutdown OK for {service_name} [PID {getpid()}]")

        time.sleep(2)
        debug(f"{service_name} worker PID [{getpid()}]: exiting")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    while True:
        if hasattr(signal, 'pause'):
            signal.pause()
        else:
            time.sleep(60)


if __name__ == '__main__':
    DArgs = json.loads(argv[-1])
    print("**CHILD WORKER DARGS:", DArgs)
    _service_worker(**DArgs)
