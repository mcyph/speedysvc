import time
from multiprocessing import cpu_count

from shmrpc.logger.std_logging.LoggerServer import LoggerServer
from shmrpc.rpc.network.NetworkServer import NetworkServer
from shmrpc.rpc.shared_memory.SHMServer import SHMServer
from shmrpc.service_managers.multi_process_manager.MultiProcessManager import \
    MultiProcessServer
from shmrpc.logger.time_series_data.ServiceTimeSeriesData import ServiceTimeSeriesData
from shmrpc.toolkit.io.make_dirs import make_dirs
from shmrpc.toolkit.py_ini.read.ReadIni import ReadIni
from shmrpc.web_monitor.app import web_service_manager, run_server


# A variable to make sure the servers stay
# persistent, and won't be garbage-collected
__LServers = []


def run_multi_proc_server(server_methods,
                          log_dir='/tmp',
                          tcp_bind='127.0.0.1',
                          max_proc_num=cpu_count(),
                          min_proc_num=1,
                          wait_until_completed=True,
                          force_insecure_serialisation=False):

    # TODO: Run this method in a separate process, so as to allow for

    print(f"{server_methods.name} parent: starting service")
    #LOG_DIR = f'/tmp/langlynx_svc'
    make_dirs(f"{log_dir}/{server_methods.name}")

    service_time_series_data = ServiceTimeSeriesData(
        path=f'{log_dir}/{server_methods.name}/'
             f'time_series_data.bin'
    )
    logger_server = LoggerServer(
        log_dir=f'{log_dir}/{server_methods.name}/',
        server_methods=server_methods
    )

    __LServers.append(MultiProcessServer(
        service_time_series_data,
        logger_server,
        server_methods,
        NetworkServer(
            server_methods,
            tcp_bind_address=tcp_bind,
            force_insecure_serialisation=force_insecure_serialisation
        ), # TODO: What if TCP bind is None, indicating not to use a network server?
        SHMServer(),
        max_proc_num=max_proc_num,
        min_proc_num=min_proc_num,
        wait_until_completed=wait_until_completed
    ))
    web_service_manager.add_service(__LServers[-1])


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
        'max_proc_num': greater_than_0_int,
        'min_proc_num': greater_than_0_int,
        'wait_until_completed': convert_bool
    }

    if 'defaults' in DValues:
        DDefaults = DValues.pop('defaults')
        DDefaults = {k: DArgKeys[k](v) for k, v in DDefaults.items()}
    else:
        DDefaults = {}

    for section, DSection in DValues.items():
        print("SECTION:", section)
        import_from = DSection.pop('import_from')
        server_methods = getattr(importlib.import_module(import_from), section) # Package?

        DArgs = DDefaults.copy()
        DArgs.update({k: DArgKeys[k](v) for k, v in DSection.items()})
        run_multi_proc_server(server_methods, **DArgs)

    print("Services started - starting web monitoring interface")

    # OPEN ISSUE: Allow binding to a specific address here? ====================================
    # For security reasons, it's probably (in almost all cases)
    # better to only allow on localhost, to prevent other people
    # stopping services, etc
    run_server(debug=False)
