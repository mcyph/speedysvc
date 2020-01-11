import time
import json
import importlib
from sys import argv
from os import getpid

from shmrpc.logger.std_logging.LoggerClient import LoggerClient
from shmrpc.rpc.network.NetworkServer import NetworkServer
from shmrpc.rpc.shared_memory.SHMServer import SHMServer


def _service_worker(init_resources, server_methods,
                    tcp_bind=None, tcp_compression=None,
                    tcp_allow_insecure_serialisation=False):
    """
    In child processes of MultiProcessManager
    """
    print(f"{server_methods.name} child: Creating logger client")
    logger_client = LoggerClient(server_methods)
    print(f"{server_methods.name} child: Creating server methods")
    smi = server_methods(logger_client)
    print(f"{server_methods.name} child: "
          f"Server methods created, starting implementations")

    L = []

    if tcp_bind and False:
        if tcp_compression == FIXME:
            pass
        else:
            raise Exception()

        L.append(NetworkServer(
            tcp_bind_address=tcp_bind,
            server_methods=smi,  # TODO: REUSE THE SAME SOCKET!!!! ====================================================
            # https://stackoverflow.com/questions/2989823/how-to-pass-file-descriptors-from-parent-to-child-in-python
            sock=FIXME,
            force_insecure_serialisation=tcp_allow_insecure_serialisation
        ))

    L.append(SHMServer()(
        server_methods=smi,
        init_resources=init_resources
    ))

    # Tell the logger server that a child has properly loaded:
    # this helps to make sure if processes are loaded properly,
    # if one depends on another.
    logger_client.set_service_status('started')

    try:
        while 1:
            time.sleep(10)
    except KeyboardInterrupt:
        print(f"Intercepted keyboard interrupt for {smi.name} [PID {getpid()}]")
        for inst in L:
            if hasattr(inst, 'shutdown'):
                print(f"Calling shutdown for {smi.name} [PID {getpid()}]..")
                inst.shutdown()
                print(f"Shutdown OK for {smi.name} [PID {getpid()}]")

        time.sleep(2)
        print("_service_worker: exiting PID", getpid())
        logger_client.shutdown()
        #logger_client.client.client_lock.close()
        #logger_client.client.server_lock.close()
        raise SystemExit


if __name__ == '__main__':
    DArgs = json.loads(argv[-1])
    #print("**CHILD WORKER DARGS:", DArgs)
    DArgs['server_methods'] = getattr(
        importlib.import_module(DArgs.pop('import_from')),
        DArgs.pop('section')
    )
    _service_worker(**DArgs)
