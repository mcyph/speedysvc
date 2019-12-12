from flask import Flask, send_from_directory
app = Flask(__name__)


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
# Update from data periodically
#================================================#


@app.route('/poll')
def poll():
    return "Hello World!"


#================================================#
# Manage services
#================================================#


@app.route('/start_service')
def start_service():
    return "ok"


@app.route('/stop_service')
def stop_service():
    return "ok"


@app.route('/restart_service')
def restart_service():
    return "ok"


if __name__ == '__main__':
    app.run()
