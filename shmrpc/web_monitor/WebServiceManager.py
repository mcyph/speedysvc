from datetime import datetime
from flask import render_template_string


LColours = [
    'red', 'green', 'blue',
    'purple', 'orange', 'brown',
    'pink', 'cyan', 'magenta',
    'yellow'
]


class WebServiceManager:
    def __init__(self):
        self.DServices = {}

    def iter_services_by_name(self):
        for service in sorted(
            self.DServices.values(),
            key=lambda service: service.name.lower()
        ):
            yield service

    def iter_services_by_port(self):
        for service in sorted(
            self.DServices.values(),
            key=lambda service: service.port
        ):
            yield service

    def iter_service_ports(self):
        for port in sorted(self.DServices):
            yield port

    #=====================================================================#
    #                        Manage Web Services                          #
    #=====================================================================#

    def add_service(self, service):
        self.DServices[service.port] = service

    def remove_service(self, port):
        del self.DServices[port]

    def restart_service(self, port):
        raise NotImplementedError()  # TODO!

    def stop_service(self, port):
        raise NotImplementedError()  # TODO!

    #=====================================================================#
    #                      Get Service Status/Stats                       #
    #=====================================================================#

    def get_overall_service_table(self):
        L = []
        for service in self.iter_services_by_name():
            L.append(self.get_D_service_info(service.port))
        return L

    def get_D_service_info(self, port, console_offset=None):
        service = self.DServices[port]
        stsd = service.service_time_series_data
        recent_values = stsd.get_recent_values()
        offset, LHTML = service.logger_server.fifo_json_log.get_html_log(
            console_offset
        )

        D = {
            "graphs": self.__get_D_graphs(recent_values),
            "console_text": '\n'.join(LHTML),
            "console_offset": offset,
            "port": port,
            "name": service.name,
            "implementations": [
                implementation.__class__.__name__
                for implementation
                in service.server_providers
            ],
            "status": service.get_status_as_string(),
            'workers': len(service.LPIDs),  # TODO: MAKE BASED ON INTERFACE, NOT IMPLEMENTATION!
            'physical_mem': recent_values[0]['physical_mem']//1024//1024,  # CHECK ME! =================================
            'cpu': recent_values[0]['cpu_usage_pc'],
        }
        D["table_html"] = self.__get_table_html(D)
        return D

    def __get_D_graphs(self, recent_values):
        labels = [
            datetime.utcfromtimestamp(D['timestamp']).strftime(
                '%m/%d %H:%M:%S'
            ) for D in recent_values
        ]
        return {
            "labels": labels,
            "ram": self.__get_data_for_keys(
                recent_values,
                'shared_mem', 'physical_mem', 'virtual_mem',
                divisor=1024 * 1024
            ),
            "io": self.__get_data_for_keys(
                recent_values,
                'io_read', 'io_written',
                divisor=1024 * 1024
            ),
            "cpu": self.__get_data_for_keys(
                recent_values,
                'cpu_usage_pc'
            ),
        }

    def __get_data_for_keys(self, values, *keys, divisor=None):
        LData = []
        for x, key in enumerate(keys):
            LOut = []
            for D in values:
                i = D[key]
                if divisor is not None:
                    i //= divisor
                LOut.append(i)
            LData.append([key, LOut, LColours[x]])
        return LData

    def __get_table_html(self, DService):
        return render_template_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table([DService]) }}',
            DService=DService
        )
