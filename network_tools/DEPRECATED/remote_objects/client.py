from pickle import dumps, loads
from _thread import get_ident
import socket

DSocks = {}

def get_sock():
    id = get_ident()
    if not id in DSocks:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("localhost", 9998))
        DSocks[id] = sock
    return DSocks[id]


def send(data):
    print('send:', [data])
    get_sock().sendall(data)

def recv(amount, sock=None):
    #print 'recv:', amount,
    s = ''
    sock = sock or get_sock()

    while 1:
        if amount <= 0:
            break
        a = sock.recv(amount)

        if a:
            #print 'RECV:', [a], len(a)
            amount -= len(a)
            s += a
        else:
            raise Exception("connection terminated")

    assert amount==0
    #print [s]
    return s

def recv_line(sock=None):
    #print 'recv_line:',
    sock = sock or get_sock()

    L = []
    while 1:
        c = sock.recv(1)
        if c == '\n':
            break
        elif c:
            L.append(c)
        else:
            raise Exception("connection terminated")

    r = ''.join(L)
    #print [r]
    return r

def handle_response():
    print('RECV LINE:', end=' ')
    typ, _, data = recv_line().partition('\t')
    print(typ, _, data)

    if typ == 'object':
        return Object(int(data))
    elif typ == 'pickle':
        amount = int(data)
        #print amount
        o = loads(recv(amount))

        if isinstance(o, Exception):
            raise o
        else:
            return o

def import_(cmd):
    send(
        'import\t%s\n' % cmd
    )
    return handle_response()

class Object:
    def __init__(self, id):
        self.id = int(id)

    def __del__(self):
        send('garbage_collect\t%s\n' % self.id)
        handle_response()

    def __getattr__(self, attr):
        if attr == 'id':
            return self.__dict__[attr]

        send('get_attr\t%s\t%s\n' % (
            self.id, attr
        ))
        return handle_response()

    def __setattr__(self, attr, o):
        if attr == 'id':
            self.__dict__[attr] = o
            return

        send = dumps(o)
        send('set_attr\t%s\t%s\t%s\n%s' % (
            self.id, attr, len(send), send
        ))
        handle_response()

    def __call__(self, *args, **kw):
        # id, args_amount, kw_amount \n
        args = dumps(args)
        kw = dumps(kw)

        send('call\t%s\t%s\t%s\n%s%s' % (
            self.id, len(args), len(kw),
            args, kw
        ))
        return handle_response()

if __name__ == '__main__':
    o = import_('import sys')
    print(o.byteorder)
    print(o.getfilesystemencoding())

    del o

    while 1:
        pass
