import sys
from datetime import datetime

#from speedysvc.Services import Services


LColours = [
    'red', 'green', 'blue',
    'purple', 'orange', 'brown',
    'pink', 'cyan', 'magenta',
    'yellow'
]


class WebServiceManager:
    def __init__(self, jinja2_env):
        self.jinja2_env = jinja2_env
        self.services = None
        self.logger_parent = None

    def set_services(self, services: 'Services'):
        self.services = services

    def set_logger_parent(self, logger_parent):
        """
        Set the logger parent (a FIFOJSONLog instance)
        :param logger_parent:
        :return:
        """
        # TODO: Move this somewhere more appropriate!
        self.logger_parent = logger_parent

    #=====================================================================#
    #                        Manage Web Services                          #
    #=====================================================================#

    def start_service(self, port):
        self.services.start_service_by_port(port)

    def stop_service(self, port):
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
        offset, LHTML = self.logger_parent.get_html_log(offset=offset)
        return offset, '<br>'.join(LHTML) + ('<br>' if LHTML else '')

    def get_overall_table_html(self, add_links=True):
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table(LServiceTable, add_links) }}'
        ).render(
            LServiceTable=self.get_overall_service_table(),
            add_links=add_links,
        )

    def get_overall_service_table(self):
        L = []
        for service_name, service in self.services.iter_services_by_name():
            L.append(self.get_D_service_info(service.get_port()))
        return L

    def get_overall_service_methods(self, max_methods=15):
        """
        Get a summary of the methods from all services, sorted
        by total time the method has taken over all calls
        :param max_methods:
        :return:
        """
        L = []
        for service_name, service in self.services.iter_services_by_name():
            DMethodStats = service.get_logger_server().get_D_method_stats()
            L.extend([
                (
                    service.get_port(),
                    service_name,
                    method_name,
                    D['num_calls'],
                    D['avg_call_time'],
                    D['total_time']
                )
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
            '{{ overall_method_stats_html(method_stats_list) }}'
        ).render(
            method_stats_list=L,
        )

    #=====================================================================#
    #                   Get Single Service Status/Stats                   #
    #=====================================================================#

    def get_D_service_info(self, port, console_offset=None):
        service = self.services.get_service_by_port(port)
        stsd = service.get_logger_server().service_time_series_data
        recent_values = stsd.get_recent_values()
        offset, LHTML = service.logger_server.fifo_json_log.get_html_log(offset=console_offset)
        method_stats_html = self.get_method_stats_html(port)

        D = {
            "graphs": self.__get_D_graphs(recent_values),
            "console_text": '\n'.join(LHTML),
            "console_offset": offset,
            "method_stats_html": method_stats_html,
        }
        D.update(self.__get_D_table_info(port, recent_values))
        D["table_html"] = self.__get_table_html(D)
        return D

    def get_method_stats_html(self, port):
        service = self.services.get_service_by_port(port)
        DMethodStats = service.get_logger_server().get_D_method_stats()

        method_stats_list = [
            (method_name, D['num_calls'], D['avg_call_time'], D['total_time'])
            for method_name, D
            in DMethodStats.items()
        ]
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import method_stats_html %}\n'
            '{{ method_stats_html(method_stats_list) }}'
        ).render(method_stats_list=method_stats_list)

    def __get_D_table_info(self, port, recent_values):
        service = self.services.get_service_by_port(port)
        return {
            "port": service.get_port(),
            "name": service.get_service_name(),
            "bound_to_tcp": service.get_tcp_bind(),
            "status": service.get_logger_server().get_service_status(),
            'workers': len(service.get_logger_server().LPIDs),  # TODO: MAKE BASED ON INTERFACE, NOT IMPLEMENTATION!
            'physical_mem': recent_values[-1]['physical_mem'] // 1024 // 1024,
            # We'll average over 3 iterations, as this can spike pretty quickly.
            # Note that recent_values is actually reversed for displaying on the graph rtl
            'cpu': round(sum([recent_values[-x]['cpu_usage_pc'] for x in range(3)]) / 3),
        }

    def __get_D_graphs(self, recent_values):
        labels = [datetime.utcfromtimestamp(D['timestamp']).strftime('%H:%M:%S')
                  for D in recent_values]
        
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

    def __get_table_html(self, service_dict):
        return self.jinja2_env.from_string(
            '{% from "service_macros.html" import service_status_table %}\n'
            '{{ service_status_table([service_dict]) }}'
        ).render(service_dict=service_dict)
