import sys
import time
import json
import signal
import importlib
from sys import argv
from os import getpid

from speedysvc.logger.std_logging.LoggerClient import LoggerClient
from speedysvc.client_server.network.NetworkServer import NetworkServer
from speedysvc.client_server.shared_memory.SHMServer import SHMServer


def debug(*s):
    if False:
        print(*s)


def _service_worker(server_methods):
    """
    In child processes of MultiProcessManager
    """
    debug(f"{server_methods.name} child: Creating logger client")
    logger_client = LoggerClient(server_methods)
    debug(f"{server_methods.name} child: Creating server methods")
    smi = server_methods(logger_client)
    debug(f"{server_methods.name} child: "
          f"Server methods created, starting implementations")

    L = []
    L.append(SHMServer(server_methods=smi))

    # Tell the logger server that a child has properly loaded:
    # this helps to make sure if processes are loaded properly,
    # if one depends on another.
    logger_client.set_service_status('started')

    debug(f"{server_methods.name} worker PID [{getpid()}]: "
          f"Server methods created - listening for commands")

    _handling_sigint = [False]
    def signal_handler(sig, frame):
        if _handling_sigint[0]:
            return
        _handling_sigint[0] = True

        print(f"Intercepted keyboard interrupt for {smi.name} [PID {getpid()}]")
        for inst in L:
            if hasattr(inst, 'shutdown'):
                debug(f"Calling shutdown for {smi.name} [PID {getpid()}]..")
                inst.shutdown()
                debug(f"Shutdown OK for {smi.name} [PID {getpid()}]")

        time.sleep(2)
        debug(f"{smi.name} worker PID [{getpid()}]: exiting")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    while True:
        if hasattr(signal, 'pause'):
            signal.pause()
        else:
            time.sleep(60)


if __name__ == '__main__':
    DArgs = json.loads(argv[-1])
    #print("**CHILD WORKER DARGS:", DArgs)
    DArgs['server_methods'] = getattr(
        importlib.import_module(DArgs.pop('import_from')),
        DArgs.pop('section')
    )
    _service_worker(**DArgs)
