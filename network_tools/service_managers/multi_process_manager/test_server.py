from network_tools.logger.LoggerServer import LoggerServer
from network_tools.rpc.base_classes.ServerMethodsBase import \
    ServerMethodsBase
from network_tools.rpc.network.NetworkServer import NetworkServer
from network_tools.rpc.shared_memory.SHMServer import SHMServer
from network_tools.service_managers.multi_process_manager.MultiProcessManager import \
    MultiProcessServer
from network_tools.logger.ServiceTimeSeriesData import ServiceTimeSeriesData
from network_tools.rpc_decorators import json_method
from toolkit.io.make_dirs import make_dirs


class TestServerMethods(ServerMethodsBase):
    port = 5557
    name = 'multiprocess_echo_serv'

    @json_method
    def cpu_intensive_method(self):
        for x in range(1000000):
            pass
        return "done!"


if __name__ == '__main__':
    PATH = '/tmp/mpm_test'
    make_dirs(PATH)

    service_time_series_data = ServiceTimeSeriesData(
        path=f'{PATH}/time_series_data.bin'
    )
    logger_server = LoggerServer(
        log_dir=PATH,
        server_methods=TestServerMethods
    )
    print("LOGGER SERVER STARTED!")

    n = NetworkServer(
            TestServerMethods,
            tcp_bind_address='127.0.0.1'
        )
    s =SHMServer()
    print("CREATING!")

    mps = MultiProcessServer(
        service_time_series_data,
        logger_server,
        TestServerMethods,
        n, s
    )
    print("CREATED")

    import time
    while 1:
        time.sleep(10)
