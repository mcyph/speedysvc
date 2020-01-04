import os
import json
from flask import Flask, send_from_directory, render_template, request
from shmrpc.web_monitor.WebServiceManager import WebServiceManager


app = Flask(
    __name__,
    template_folder=os.path.join(
        os.path.dirname(__file__), 'templates'
    )
)
web_service_manager = WebServiceManager()


def run_server(services=(), debug=False):
    """
    Should be called with a list of
    MultiProcessManager's and/or InProcessManager's
    """
    for service in services:
        web_service_manager.add_service(service)

    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=debug)


#================================================#
# Static file serving
#================================================#


@app.route('/static/<path:path>')
def send_js(path):
    # Probably not needed, but to be absolutely certain..
    assert not '..' in path
    assert not '//' in path
    assert path[0] != '/'
    return send_from_directory('static', path)


#================================================#
# Main index methods
#================================================#


@app.route('/')
def index():
    console_offset, console_text = web_service_manager.get_overall_log()
    return render_template(
        "index.html",
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


@app.route('/poll')
def poll():
    service_table_html = web_service_manager.get_overall_table_html(add_links=True)
    console_offset, console_text = web_service_manager.get_overall_log(
        offset=int(request.args.get('offset'))
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


@app.route('/service_info')
def service_info():
    port = int(request.args.get('port'))
    DService = web_service_manager.get_D_service_info(port)

    return render_template(
        "service_info.html",
        service_name=DService['name'],
        port=port,
        DService=DService
    )


@app.route('/poll_service_info')
def poll_service_info():
    port = int(request.args.get('port'))
    console_offset = int(request.args.get('console_offset'))
    DServiceInfo = web_service_manager.get_D_service_info(
        port, console_offset
    )
    return json.dumps(DServiceInfo)


#================================================#
# Manage services
#================================================#


@app.route('/start_service')
def start_service():
    port = int(request.args.get('port'))
    web_service_manager.start_service(port)
    return "ok"


@app.route('/stop_service')
def stop_service():
    port = int(request.args.get('port'))
    web_service_manager.stop_service(port)
    return "ok"


@app.route('/restart_service')
def restart_service():
    port = int(request.args.get('port'))
    web_service_manager.restart_service(port)
    return "ok"

