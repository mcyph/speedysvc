#import sys
import _thread
#from Queue import Queue
#from TempQueue import temp_queue
from .LargeFile import LargeFile


if True: 
    FILEINST = open
else: 
    FILEINST = LargeFile # WARNING!


# If True, then the index files are loaded into memory
USE_CSTRINGIO = False
from io import StringIO


def read_line(f):
    if 1: 
        return f.readline()
    
    #if 1: 
    #   return f.read(2101)
    
    LData = []
    amount = 512
    
    while 1:
        Data = f.read(amount) # TODO: BENCHMARK ME!
        if '\n' in Data:
            LData.append('%s\n' % Data.split('\n')[0])
            break
        else: 
            LData.append(Data)
            amount *= 2
    
    print(len(''.join(LData)))
    return ''.join(LData)


# The file read-ahead buffer
# -1: 22.4secs
# 1: 24.5secs
# 128: 26secs
# 512: 24.5secs
BUFFER = -1


class Thread:
    def __init__(self):
        self.Lock = _thread.allocate_lock()
        
        # Store the actual files by key and value The value 
        # might be None if there are too many files open. Keys of subvalues: 
        # usage -> Store how many times a file has been open
        # args -> Store the arguments used to init a file (path, mode)
        # f -> Store the file itself
        self.DFiles = {}
        # Store how many files are open. There's a limit on open 
        # files and files are opened and closed as needed
        self.open_files = 0
    
    def __get_file(self, path, mode):
        self.__close_unused_files()
        
        key = (path, mode)
        if key in self.DFiles:
            if self.DFiles[key]['file']:
                # f already open, return it
                return self.DFiles[key]['file']
            else:
                # Otherwise, recreate it
                f = FILEINST(path, mode, BUFFER)
                f = self.__get_CStringIO(f)
                
                self.DFiles[key]['file'] = f
                self.open_files += 1
                return f
        else:
            # Create a new file instance
            f = FILEINST(path, mode, BUFFER)
            f = self.__get_CStringIO(f)
            
            self.DFiles[key] = {'usage': 1, 
                                'args': (path, mode), 
                                'file': f}
            self.open_files += 1
            return f
        
    def __get_CStringIO(self, f):
        if USE_CSTRINGIO:
            old_file = f
            f = StringIO(old_file.read())
            old_file.close()
        return f
        
    def __close_unused_files(self):
        if self.open_files > 150:
            # There's a limit of say, 512 files open at once on 
            # some OSes. This closes the files which are least used
            LFiles = [(self.DFiles[k]['usage'], self.DFiles[k]['file']) for k in self.DFiles]
            LFiles.sort()
            # Chop off the top one by number of opens :-)
            LFiles[0][1].close()
            self.open_files -= 1
    
    def acquire_lock(self, LFileArgs):
        # TODO: ADD A TIMEOUT VALUE?
        # TODO: ADD FILE-SPECIFIC LOCKS?
        
        #print 'GETTING LOCK!'
        if self.Lock.acquire():
            return self.__get_file(*LFileArgs)
        
        while 1:
            if self.Lock.acquire(1):
                return self.__get_file(*LFileArgs)
    
    def release_lock(self):
        #print 'RELEASING LOCK!'
        self.Lock.release()
    
    def readline(self, LFileArgs, seek):
        #print 'READLINE!'
        f = self.acquire_lock(LFileArgs)
        
        try:
            if seek: f.seek(*seek)
            #Rtn = f.readline()
            Rtn = read_line(f)
        except:
            self.release_lock()
            raise
        
        self.release_lock()
        #print 'READLINE OK!'
        return Rtn
    
    def read(self, LFileArgs, amount, seek):
        f = self.acquire_lock(LFileArgs)
        
        try:
            if seek: f.seek(*seek)
            Rtn = f.read(amount)
        except: 
            self.release_lock()
            raise
        
        self.release_lock()
        return Rtn
    
    def read_multiple(self, LFileArgs, L):
        # Read multiple areas of the file, making up
        # for the difference between threads
        f = self.acquire_lock(LFileArgs)
        
        try:
            LResult = []
            for amount, seek in L:
                f.seek(*seek)
                LResult.append(f.read(amount))
        except: 
            self.release_lock()
            raise
        
        self.release_lock()
        return LResult
    
    def write(self, LFileArgs, data, seek):
        f = self.acquire_lock(LFileArgs)
        
        try:
            if seek: 
                f.seek(*seek)
            
            seek = f.tell()
            amount = len(data)
            f.write(data)
        except:
            self.release_lock()
            raise
        
        self.release_lock()
        return seek, amount
    
    def close(self, LFileArgs):
        # close the file and set it to None to prevent 
        # errors working on closed files :-)
        f = self.acquire_lock(LFileArgs)
        
        try:
            self.DFiles[tuple(LFileArgs)]['file'] = None
            f.close()
            self.open_files -= 1
        except:
            self.release_lock()
            raise
        
        self.release_lock()


Thread = Thread()


class ThreadedFile:
    # A multi-threaded file. Useful when multiple people need to read/write 
    # to dictionary indexes at once. Note that 'seek' is added to the read 
    # and write to prevent multiple "Thread.seek()" calls overlapping when 
    # working from multiple threads causing corruption
    def __init__(self, path, mode): 
        self.LFileArgs = (path, mode)
    
    def read_multiple(self, L): 
        return Thread.read_multiple(self.LFileArgs, L)
    
    def readline(self, seek=None): 
        return Thread.readline(self.LFileArgs, seek)
    
    def read(self, amount=None, seek=None): 
        return Thread.read(self.LFileArgs, amount, seek)
    
    def write(self, data, seek=None): 
        return Thread.write(self.LFileArgs, data, seek)
    
    def tell(self): 
        return Thread.tell(self.LFileArgs)
    
    def flush(self): 
        return Thread.flush(self.LFileArgs)
    
    def close(self): 
        return Thread.close(self.LFileArgs)


class f:
    # A single-threaded file. Useful for dictionaries  when importing to 
    # increase speed
    def __init__(self, path, mode):
        self.f = FILEINST(path, mode, BUFFER)
    
    def readline(self, seek=None):
        if seek: 
            self.f.seek(*seek)
        
        return self.f.readline()
    
    def read(self, amount=None, seek=None):
        if seek: 
            self.f.seek(*seek)
        
        return self.f.read(amount)
    
    def read_multiple(self, L):
        LRtn = []
        for amount, seek in L:
            self.f.seek(*seek)
            LRtn.append(self.f.read(amount))
        return LRtn
    
    def write(self, data, seek=None):
        if seek: 
            self.f.seek(*seek)
        
        seek = self.f.tell()
        amount = len(data)
        self.f.write(data)
        return seek, amount
        
    #def tell(self): 
    #   return self.f.tell()
    
    def flush(self): 
        self.f.flush()
    
    def close(self): 
        self.f.close()
