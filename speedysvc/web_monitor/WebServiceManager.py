import sys
from datetime import datetime


LColours = [
    'red', 'green', 'blue',
    'purple', 'orange', 'brown',
    'pink', 'cyan', 'magenta',
    'yellow'
]


class WebServiceManager:
    def __init__(self, jinja2_env):
        self.jinja2_env = jinja2_env
        self.DServices = {}  # TODO: Replace me, directly using the Services instance!

    def set_services(self, services):
        self.services = services

    def set_logger_parent(self, logger_parent):
        """
        Set the logger parent (a FIFOJSONLog instance)
        :param logger_parent:
        :return:
        """
        # TODO: Move this somewhere more appropriate!
        self.logger_parent = logger_parent

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
        self.DServices[service.original_server_methods.port] = service

    def remove_service(self, port):
        """

        :param port:
        :return:
        """
        del self.DServices[port]

    def start_service(self, port):
        """

        :param port:
        :return:
        """
        self.services.start_service_by_port(port)

    def stop_service(self, port):
        """

        :param port:
        :return:
        """
        self.services.stop_service_by_port(port)

    #=====================================================================#
    #                     Get All Service Status/Stats                    #
    #=====================================================================#

    def get_overall_log(self, offset=None):
        """
        Get the "overall" log for all services
        :param offset:
        :return:
        """
        offset, LHTML = self.logger_parent.get_html_log(
            offset=offset
        )
        return offset, '<br>'.join(LHTML) + ('<br>' if LHTML else '')

    def get_overall_table_html(self, add_links=True):
        """

        :param add_links:
        :return:
        """
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table(LServiceTable, add_links) }}'
        ).render(
            LServiceTable=self.get_overall_service_table(),
            add_links=add_links
        )

    def get_overall_service_table(self):
        """

        :return:
        """
        L = []
        for service in self.iter_services_by_name():
            L.append(self.get_D_service_info(service.original_server_methods.port))
        return L

    def get_overall_service_methods(self, max_methods=15):
        """
        Get a summary of the methods from all services, sorted
        by total time the method has taken over all calls
        :param max_methods:
        :return:
        """
        L = []
        for service in self.iter_services_by_name():
            DMethodStats = service.get_D_method_stats()

            L.extend([
                (
                    service.original_server_methods.port,
                    service.original_server_methods.name,
                    method_name,
                    D['num_calls'],
                    D['avg_call_time'],
                    D['total_time'])
                for method_name, D
                in DMethodStats.items()
            ])

        L.sort(key=lambda i: -i[-1])
        if max_methods is not None:
            L = L[:max_methods]

        return L

    def get_overall_service_methods_html(self, max_methods=15):
        L = self.get_overall_service_methods(max_methods)
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import overall_method_stats_html %}\n'
            '{{ overall_method_stats_html(LMethodStats) }}'
        ).render(
            LMethodStats=L
        )

    #=====================================================================#
    #                   Get Single Service Status/Stats                   #
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
        offset, LHTML = service.fifo_json_log.get_html_log(
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
        DMethodStats = self.DServices[port].get_D_method_stats()

        LMethodStats = [
            (method_name, D['num_calls'], D['avg_call_time'], D['total_time'])
            for method_name, D
            in DMethodStats.items()
        ]
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import method_stats_html %}\n'
            '{{ method_stats_html(LMethodStats) }}'
        ).render(
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
            "name": service.original_server_methods.name,
            "bound_to_tcp": service.tcp_bind,
            "status": service.get_service_status(),
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
                *(
                    ('shared_mem', 'physical_mem', 'virtual_mem')
                    if sys.platform != 'win32'
                    else ('physical_mem', 'virtual_mem')
                ),
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
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table([DService]) }}'
        ).render(
            DService=DService
        )
