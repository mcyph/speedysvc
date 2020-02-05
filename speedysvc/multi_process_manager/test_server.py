from speedysvc.logger.LoggerServer import LoggerServer
from speedysvc.rpc.base_classes.ServerMethodsBase import \
    ServerMethodsBase
from speedysvc.rpc.network.NetworkServer import NetworkServer
from speedysvc.rpc.shared_memory.SHMServer import SHMServer
from speedysvc.service_managers.multi_process_manager.MultiProcessManager import \
    MultiProcessServer
from speedysvc.logger.ServiceTimeSeriesData import ServiceTimeSeriesData
from speedysvc.rpc_decorators import pickle_method
from speedysvc.toolkit.io.make_dirs import make_dirs


class TestServerMethods(ServerMethodsBase):
    port = 5557
    name = 'multiprocess_echo_serv'

    @pickle_method
    def cpu_intensive_method(self, echo_me):
        #for x in range(1000000):
        #    pass
        return echo_me


if __name__ == '__main__':
    PATH = '/tmp/mpm_test'
    make_dirs(PATH)

    service_time_series_data = ServiceTimeSeriesData(
        path=f'{PATH}/time_series_data.bin')
    logger_server = LoggerServer(log_dir=PATH,
                                 server_methods=TestServerMethods)
    print("LOGGER SERVER STARTED!")

    n = NetworkServer(TestServerMethods,
                      tcp_bind_address='127.0.0.1')
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
