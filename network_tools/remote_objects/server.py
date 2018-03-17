import inspect
import toolkit
#import uni_tools

from types import (
    InstanceType, ClassType, FunctionType, BuiltinFunctionType,
    BuiltinMethodType, LambdaType, CodeType, GeneratorType,
    UnboundMethodType, MethodType, ModuleType, ObjectType
)

from cPickle import dumps, loads
import SocketServer

SNoPickle = set([
    InstanceType, ClassType, FunctionType, BuiltinFunctionType,
    BuiltinMethodType, LambdaType, CodeType, GeneratorType,
    UnboundMethodType, MethodType, ModuleType, ObjectType, type
])

from client import recv_line, recv

var_id = 0
DVars = {}

from socket import *

sock=socket()
sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

class Server(SocketServer.ThreadingMixIn, SocketServer.BaseRequestHandler):
    allow_reuse_address = True

    def __init__(self, *args, **kw):
        self.allow_reuse_address = True
        SocketServer.BaseRequestHandler.__init__(
            self, *args, **kw
        )


    def handle(self):
        while 1:
            line = recv_line(self.request)
            #print 'cmd:', line.rstrip('\n')
            if not line:
                return

            cmd, _, data = line.rstrip('\n').partition('\t')

            try:
                self._handle(cmd, data)
            except Exception, exc:
                from traceback import print_exc
                print_exc()
                self._handle_obj(exc)

    def _handle(self, cmd, data):
        if cmd == 'import':
            # called like "from module import xx"
            exec(data+' as temp_obj')
            self._handle_obj(temp_obj)
            del temp_obj

        elif cmd == 'get_attr':
            id, _, attr = data.partition('\t')
            o = DVars[int(id)]
            attr = getattr(o, attr)
            self._handle_obj(attr)

        elif cmd == 'set_attr':
            id, attr, amount = data.split('\t')
            o = DVars[int(id)]

            set_to = loads(recv(int(amount), self.request))
            setattr(o, attr, set_to)
            self._handle_obj('OK')

        elif cmd == 'garbage_collect':
            del DVars[int(data)]
            self._handle_obj('OK')

        elif cmd == 'call':
            id, args_amount, kw_amount = data.split('\t')

            #print 'READ1:', args_amount
            args = loads(recv(int(args_amount), self.request))
            #print 'READ2:', kw_amount
            kw = loads(recv(int(kw_amount), self.request))

            #print args, kw

            o = DVars[int(id)](*args, **kw)
            self._handle_obj(o)

    def _handle_obj(self, o, force=False):
        #print 'handle:', o, type(o)

        if force or type(o) in SNoPickle:
            global var_id
            var_id += 1
            DVars[var_id] = o
            send = 'object\t%s\n' % var_id
        else:
            try:
                data = dumps(o)
            except TypeError:
                print 'TYPE WARNING:', [o]
                return self._handle_obj(o, force=True)

            send = 'pickle\t%s\n%s' % (len(data), data)

        #print 'send:', [send]
        self.request.sendall(send)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


if __name__ == "__main__":
    import threading
    import time

    # Create the server, binding to localhost on port 9999
    server = ThreadedTCPServer(("localhost", 9998), Server)

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    while 1:
        time.sleep(100)
