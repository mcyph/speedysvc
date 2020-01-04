import math
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
        """

        :return:
        """
        for service in sorted(
            self.DServices.values(),
            key=lambda service: service.name.lower()
        ):
            yield service

    def iter_services_by_port(self):
        """

        :return:
        """
        for service in sorted(
            self.DServices.values(),
            key=lambda service: service.port
        ):
            yield service

    def iter_service_ports(self):
        """

        :return:
        """
        for port in sorted(self.DServices):
            yield port

    #=====================================================================#
    #                        Manage Web Services                          #
    #=====================================================================#

    def add_service(self, service):
        """

        :param service:
        :return:
        """
        self.DServices[service.port] = service

    def remove_service(self, port):
        """

        :param port:
        :return:
        """
        del self.DServices[port]

    def restart_service(self, port):
        """

        :param port:
        :return:
        """
        raise NotImplementedError()  # TODO!

    def stop_service(self, port):
        """

        :param port:
        :return:
        """
        raise NotImplementedError()  # TODO!

    #=====================================================================#
    #                    Get Single Service Status/Stats                  #
    #=====================================================================#

    def get_overall_table_html(self, add_links=True):
        return render_template_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table(LServiceTable, add_links) }}',
            LServiceTable=self.get_overall_service_table(),
            add_links=add_links
        )

    def get_overall_service_table(self):
        """

        :return:
        """
        L = []
        for service in self.iter_services_by_name():
            L.append(self.get_D_service_info(service.port))
        return L

    #=====================================================================#
    #                    Get All Service Status/Stats                     #
    #=====================================================================#

    def get_D_service_info(self, port, console_offset=None):
        """

        :param port:
        :param console_offset:
        :return:
        """
        service = self.DServices[port]
        stsd = service.service_time_series_data
        recent_values = stsd.get_recent_values()
        offset, LHTML = service.logger_server.fifo_json_log.get_html_log(
            offset=console_offset
        )
        method_stats_html = self.get_method_stats_html(port)

        D = {
            "graphs": self.__get_D_graphs(recent_values),
            "console_text": '\n'.join(LHTML),
            "console_offset": offset,
            "method_stats_html": method_stats_html
        }
        D.update(self.__get_D_table_info(port, recent_values))
        D["table_html"] = self.__get_table_html(D)
        return D

    def get_method_stats_html(self, port):
        """

        :param port:
        :return:
        """
        DMethodStats = self.DServices[port].logger_server.get_D_method_stats()

        LMethodStats = [
            (method_name, D['num_calls'], D['avg_call_time'], D['total_time'])
            for method_name, D
            in DMethodStats.items()
        ]
        return render_template_string(
            '{% from "service_macros.html" import method_stats_html %}\n'
            '{{ method_stats_html(LMethodStats) }}',
            LMethodStats=LMethodStats
        )

    def __get_D_table_info(self, port, recent_values):
        """

        :param port:
        :param recent_values:
        :return:
        """
        service = self.DServices[port]
        return {
            "port": port,
            "name": service.name,
            "implementations": [
                implementation.__class__.__name__
                for implementation
                in service.server_providers
            ],
            "status": service.get_status_as_string(),
            'workers': len(service.LPIDs),  # TODO: MAKE BASED ON INTERFACE, NOT IMPLEMENTATION!
            'physical_mem': recent_values[-1]['physical_mem'] // 1024 // 1024,
            # We'll average over 3 iterations, as this can spike pretty quickly.
            # Note that recent_values is actually reversed for displaying on the graph rtl
            'cpu': round(sum([recent_values[-x]['cpu_usage_pc'] for x in range(3)]) / 3)
        }

    def __get_D_graphs(self, recent_values):
        """

        :param recent_values:
        :return:
        """
        labels = [
            datetime.utcfromtimestamp(D['timestamp']).strftime(
                '%H:%M:%S' # %m/%d
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
        """

        :param values:
        :param keys:
        :param divisor:
        :return:
        """
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
        """

        :param DService:
        :return:
        """
        return render_template_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table([DService]) }}',
            DService=DService
        )
