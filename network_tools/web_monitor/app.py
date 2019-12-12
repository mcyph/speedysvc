import json
from datetime import datetime
from flask import Flask, send_from_directory, render_template
app = Flask(__name__, template_folder='templates')

_services = None


def run_server(services, debug=False):
    global _services
    _services = services
    app.run(debug=debug)


#================================================#
# Main index method
#================================================#


@app.route('/')
def index():
    return "Hello World!"


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
def start_service(pid):
    return "ok"


@app.route('/stop_service')
def stop_service(pid):
    return "ok"


@app.route('/restart_service')
def restart_service(pid):
    return "ok"


#================================================#
# Update from data periodically
#================================================#


@app.route('/poll')
def poll():
    D = {}
    for service in _services:
        stsd = service.service_time_series_data
        recent_values = stsd.get_recent_values()

        labels = [
            datetime.utcfromtimestamp(ts).strftime(
                '%Y-%m-%d %H:%M:%S'
            ) for ts in recent_values
        ]
        ram = [

        ]
        io = (

        )
        cpu = (

        )

        port = str(service.port)
        assert not port in D
        D[port] = {
            "graphs": {
                "labels": labels,
                "ram": FIXME,
                "io": FIXME,
                "cpu": FIXME,
            },
            "console_text": FIXME,
            "table_html": _get_table_html(service)
        }
    return json.dumps(D)


def _get_data_for_key(key):
    pass


def _get_table_html(service):
    FIXME


if __name__ == '__main__':
    app.run()
