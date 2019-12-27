import os
import json
from datetime import datetime
from flask import Flask, send_from_directory, render_template, render_template_string

app = Flask(
    __name__,
    template_folder=os.path.join(
        os.path.dirname(__file__), 'templates'
    )
)

_DServices = {}


def run_server(services=(), debug=False):
    """
    Should be called with a list of
    MultiProcessManager's and/or InProcessManager's
    """
    for service in services:
        _DServices[str(service.port)] = service

    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=debug)


def add_service(service):
    _DServices[str(service.port)] = service


def remove_service(port):
    del _DServices[port]


#================================================#
# Main index method
#================================================#


@app.route('/')
def index():
    return render_template(
        "index.html",
        LServices=[
            _get_service_info_dict(port)
            for port in _DServices
        ],
        services_json=(
            [(service.name, service.port) for service in _DServices.values()]
        )
    )


@app.route('/static/<path:path>')
def send_js(path):
    # Probably not needed, but to be absolutely certain..
    assert not '..' in path
    assert not '//' in path
    assert path[0] != '/'
    return send_from_directory('static', path)


#================================================#
# Manage services
#================================================#


@app.route('/start_service')
def start_service(port):
    _DServices[port].start_service()
    return "ok"


@app.route('/stop_service')
def stop_service(port):
    _DServices[port].stop_service()
    return "ok"


@app.route('/restart_service')
def restart_service(port):
    _DServices[port].restart_service()
    return "ok"


#================================================#
# Update from data periodically
#================================================#


@app.route('/poll')
def poll():
    D = {}
    for port in _DServices:  # ORDER?? ============================
        assert not port in D
        D[port] = _get_service_info_dict(port)
    return json.dumps(D)


def _get_service_info_dict(port):
    service = _DServices[port]
    stsd = service.service_time_series_data
    recent_values = stsd.get_recent_values()

    labels = [
        datetime.utcfromtimestamp(D['timestamp']).strftime(
            '%m/%d %H:%M:%S'
        ) for D in recent_values
    ]

    D = {
        "graphs": {
            "labels": labels,
            "ram": _get_data_for_keys(
                recent_values,
                'shared_mem', 'physical_mem', 'virtual_mem',
                divisor=1024*1024
            ),
            "io": _get_data_for_keys(
                recent_values,
                'io_read', 'io_written',
                divisor=1024 * 1024
            ),
            "cpu": _get_data_for_keys(
                recent_values,
                'cpu_usage_pc'
            ),
        },
        "console_text": '',  # FIXME!! =========================================
        "port": port,
        "name": service.name,
        "implementations": [
            implementation.__class__.__name__
            for implementation
            in service.server_providers
        ],
        "status": service.get_status_as_string(),
        'workers': len(service.LPIDs),  # TODO: MAKE BASED ON INTERFACE, NOT IMPLEMENTATION!
        'ram': recent_values[0]['virtual_mem']//1024//1024,  # CHECK ME! =================================
        'cpu': recent_values[0]['cpu_usage_pc'],
    }
    D["table_html"] = _get_table_html(D)
    return D


LColours = [
    'red',
    'green',
    'blue',
    'purple',
    'orange',
    'brown',
    'pink',
    'cyan',
    'magenta',
    'yellow'
]


def _get_data_for_keys(values, *keys, divisor=None):
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


def _get_table_html(DService):
    return render_template_string(
        '{% from "service.html" import service_status_table %}\n'
        '{{ service_status_table(DService) }}',
        DService=DService
    )

