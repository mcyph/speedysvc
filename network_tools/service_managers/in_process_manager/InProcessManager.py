from network_tools.logger.LoggerClient import LoggerClient


class InProcessManager:
    def __init__(self,
                 service_time_series_data,
                 logger_server,
                 server_methods,
                 *server_providers
                 ):

        # TODO: Do something with these, or get rid of them?
        self.service_time_series_data = service_time_series_data
        self.logger_server = logger_server

        logger_client = self.logger_client = \
            LoggerClient(server_methods)
        smi = server_methods()

        L = self.L = []
        for provider in server_providers:
            L.append(provider(server_methods=smi))
