import json
from datetime import datetime
from flask import Flask, send_from_directory, render_template, render_template_string

app = Flask(
    __name__,
    template_folder='network_tools/web_monitor/templates/'
)

_DServices = None


def run_server(services, debug=False):
    """
    Should be called with a list of
    MultiProcessManager's and/or InProcessManager's
    """
    global _DServices
    _DServices = {}
    for service in services:
        _DServices[str(service.port)] = service
    app.run(debug=debug)


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
        ]
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
        datetime.utcfromtimestamp(ts).strftime(
            '%Y-%m-%d %H:%M:%S'
        ) for ts in recent_values
    ]

    return {
        "graphs": {
            "labels": labels,
            "ram": _get_data_for_keys(recent_values,
                'shared_mem', 'physical_mem', 'virtual_mem'
            ),
            "io": _get_data_for_keys(recent_values,
                'io_read', 'io_written'
            ),
            "cpu": _get_data_for_keys(recent_values,
                'cpu_usage_pc'
            ),
        },
        "console_text": '',
        "table_html": _get_table_html(service)
    }


def _get_data_for_keys(values, *keys):
    LData = []
    for key in keys:
        LOut = []
        for D in values:
            LOut.append(D[key])
        LData.append(LOut)
    return LData


def _get_table_html(service):
    return render_template_string(
        '{% from "service.html" import service_status_table %}\n'
        '{{ service_status_table(DService) }}',
        DService=service.FIXME
    )

