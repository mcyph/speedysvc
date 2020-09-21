import os
import json
import atexit
import cherrypy
from jinja2 import Environment, FileSystemLoader

from speedysvc.web_monitor.WebServiceManager import WebServiceManager


env = Environment(loader=FileSystemLoader(os.path.join(
    os.path.dirname(__file__), 'templates'
)))
web_service_manager = WebServiceManager(env)


def run_server(services=(), debug=False, host='127.0.0.1', port=5155):
    """
    Should be called with a list of
    MultiProcessManager's and/or InProcessManager's
    """
    for service in services:
        web_service_manager.add_service(service)

    print(f"Web interface starting on http://{host}:{port}:", end=" ")

    config = {
        'global': {
            'server.socket_host': host,
            'server.socket_port': port,
            'environment': (
                'production' if not debug else 'staging'
            ),
        },
        '/': {

        },
        '/static': {
            'tools.staticdir.root': os.path.join(
                os.path.dirname(__file__), 'static'
            ),
            'tools.staticdir.on': True,
            'tools.staticdir.dir': ""
        }
    }
    cherrypy._global_conf_alias.update(config)
    cherrypy.tree.mount(App(), '', config)

    # This call stops windows from being able to exit
    # from ctrl+c events!
    # I think it's better to just add atexit handlers
    #cherrypy.engine.signals.subscribe()

    cherrypy.engine.start()
    atexit.register(cherrypy.engine.exit)
    print("[OK]")
    print("Serving forever: use [ctrl+c] to shut down cleanly.")
    cherrypy.engine.block()


class App:
    #================================================#
    # Main index methods
    #================================================#

    @cherrypy.expose
    def index(self):
        console_offset, console_text = web_service_manager.get_overall_log()
        return env.get_template("index.html").render(
            LServices=web_service_manager.get_overall_service_table(),
            console_text=console_text,
            console_offset=console_offset,
            LOverallServiceMethods=web_service_manager.get_overall_service_methods(),
            services_json=([
                (service.name, service.port)
                for service
                in web_service_manager.iter_services_by_name()
            ])
        )

    @cherrypy.expose
    def poll(self, offset):
        service_table_html = web_service_manager.get_overall_table_html(add_links=True)
        console_offset, console_text = web_service_manager.get_overall_log(
            offset=int(offset)
        )
        overall_service_methods_html = web_service_manager.get_overall_service_methods_html()

        return json.dumps({
            'service_table_html': service_table_html,
            'overall_service_methods_html': overall_service_methods_html,
            'console_text': console_text,
            'console_offset': console_offset
        })

    #================================================#
    # Service detailed info methods
    #================================================#

    @cherrypy.expose
    def service_info(self, port):
        port = int(port)
        DService = web_service_manager.get_D_service_info(port)

        return env.get_template("service_info.html").render(
            service_name=DService['name'],
            port=port,
            DService=DService
        )

    @cherrypy.expose
    def poll_service_info(self, port, console_offset):
        port = int(port)
        console_offset = int(console_offset)
        DServiceInfo = web_service_manager.get_D_service_info(
            port, console_offset
        )
        return json.dumps(DServiceInfo)

    #================================================#
    # Manage services
    #================================================#

    @cherrypy.expose
    def start_service(self, port):
        port = int(port)
        web_service_manager.start_service(port)
        raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    def stop_service(self, port):
        port = int(port)
        web_service_manager.stop_service(port)
        raise cherrypy.HTTPRedirect('/')
