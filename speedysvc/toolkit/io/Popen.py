import sys, os
import time
import errno
import subprocess
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT


if os.name == 'nt':
    from win32file import ReadFile, WriteFile
    from win32pipe import PeekNamedPipe
    import msvcrt
else:
    import select
    import fcntl


class Popen(subprocess.Popen):
    def recv(self, maxsize=None): 
        return self._recv('stdout', maxsize)
    
    def recv_err(self, maxsize=None): 
        return self._recv('stderr', maxsize)
    
    def send_recv(self, input=b'', maxsize=None):
        return self.send(input), self.recv(maxsize), self.recv_err(maxsize)
    
    def get_conn_maxsize(self, which, maxsize):
        if maxsize is None: 
            maxsize = 1024
        elif maxsize < 1: 
            maxsize = 1
        
        return getattr(self, which), maxsize
    
    def _close(self, which):
        getattr(self, which).close()
        setattr(self, which, None)
    
    if os.name == 'nt':
        def send(self, input):
            if not self.stdin: return None
            try:
                if not hasattr(self, 'InHandle'):
                    self.InHandle = msvcrt.get_osfhandle(self.stdin.fileno())
                errCode, written = WriteFile(self.InHandle, input)
            
            except ValueError: 
                return self._close('stdin')
            
            except SystemExit: 
                raise
            
            except (subprocess.pywintypes.error, Exception) as why:
                if why[0] in (109, errno.ESHUTDOWN): 
                    return self._close('stdin')
                raise
            return written
        
        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            
            if conn is None: 
                return None
            try:
                if not hasattr(self, '%sHandle' % which):
                    setattr(self, '%sHandle' % which, msvcrt.get_osfhandle(conn.fileno()))
                Handle = getattr(self, '%sHandle' % which)
                read, nAvail, nMessage = PeekNamedPipe(Handle, 0)
                
                if maxsize < nAvail: 
                    nAvail = maxsize
                
                if nAvail > 0: 
                    errCode, read = ReadFile(Handle, nAvail, None)
            
            except ValueError: 
                return self._close(which)
            
            except SystemExit: 
                raise
            
            except (subprocess.pywintypes.error, Exception) as why:
                if why[0] in (109, errno.ESHUTDOWN): 
                    return self._close(which)
                raise
            
            if self.universal_newlines and False: 
                read = self._translate_newlines(read)
            return read
    
    else:
        def send(self, input):
            if not self.stdin:
                return None

            if not select.select([], [self.stdin], [], 0)[1]:
                return 0

            try:
                written = os.write(self.stdin.fileno(), input)
            except OSError as why:
                if why[0] == errno.EPIPE: #broken pipe
                    return self._close('stdin')
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None
            
            flags = fcntl.fcntl(conn, fcntl.F_GETFL)
            if not conn.closed:
                fcntl.fcntl(conn, fcntl.F_SETFL, flags| os.O_NONBLOCK)
            
            try:
                if not select.select([conn], [], [], 0)[0]:
                    return b''
                
                r = conn.read(maxsize)
                if not r:
                    return self._close(which)
    
                if self.universal_newlines:
                    r = self._translate_newlines(r)
                return r
            finally:
                if not conn.closed:
                    fcntl.fcntl(conn, fcntl.F_SETFL, flags)
    
    def send_all(self, data):
        while 1:
            if not data: 
                break
            
            len = self.send(data)
            if len is None: 
                raise Exception(message)
            data = data[len:]
    
    def readline(self):
        return self.stdout.readline()
    
    def recv_some(self):
        if False:
            return self.stdout.read()
        else:
            data = self.recv()
            return data


message = "Other end disconnected!"
