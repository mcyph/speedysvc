import os

# WARNING: This module was meant as a TEST, and it has 
# a slice glitch which means the end of the files are chopped!
# It also isn't any faster than just using a single file!

#MAX_SIZE = 2147483648 # 2GB
MAX_SIZE = 500000000


class LargeFile:
    def __init__(self, Path, Mode, Buffer=-1):
        self.Pos = 0
        self.Path = Path
        self.Mode = Mode
        self.Buffer = Buffer
        self.LFiles = []
        self.LPaths = []
        
        # Delete all existing files if 'w' mode
        if 'w' in Mode:
            i = 2
            while 1:
                Try = '%s_%s' % (self.Path, i)
                if os.path.exists(Try):
                    os.unlink(Try)
                else: break
                i += 1
        
        # Open existing files
        self.LFiles.append(file(Path, Mode, self.Buffer))
        self.LPaths.append(Path)
        i = 2
        while 1:
            Try = '%s_%s' % (self.Path, i)
            if os.path.exists(Try):
                nFile = file(Try, self.Mode, self.Buffer)
                self.LFiles.append(nFile)
                self.LPaths.append(Try)
            else: break
            i += 1
        
        # Register the intial filesize
        self.Size = self.get_file_size()
        
    def close(self):
        for File in self.LFiles:
            File.close()
        
    def get_file_size(self):
        # TODO: Because os.path.getsize() will be 
        # broken, RETURN THE REMAPPED FILESIZE!
        Size = 0
        for Path in self.LPaths:
            Size += os.path.getsize(Path)
        return Size
        
    def get_cur_file(self):
        # Get the file and the remainder bytes 
        # (what the seek position in that file should be)
        FileNum = int(self.Pos/MAX_SIZE)
        File = self.LFiles[FileNum]
        Remainder = self.Pos % MAX_SIZE
        return File, Remainder
        
    def open_new_file(self):
        # TODO: MAKE SURE FILE EXTENSIONS NOT MANGLED by going (FILE.EXT_NUM)!
        i = 2
        while 1:
            Try = '%s_%s' % (self.Path, i)
            if not Try in self.LPaths: # FIXME: ADD A SEPARATE LFILES WITH PATHNAMES!!!
                nFile = file(Try, self.Mode, self.Buffer)
                self.LFiles.append(nFile)
                self.LPaths.append(Try)
                return nFile
            i += 1
        
    def __iter__(self):
        while 1:
            Data = self.readline()
            if Data: yield Data
            else: break
        
    def readline(self):
        File, Remainder = self.get_cur_file()
        File.seek(Remainder) # HACK!
        print(self.LFiles.index(File), Remainder)
        
        Data = File.read(2101)
        #Data = File.readline()
        #Data = 'asdaslkdsal\n'
        if not '\n' in Data and False:
            # Continue on in the next file
            AddAmount = MAX_SIZE-Remainder
            self.Pos += AddAmount
            
            try: nFile, nRemainder = self.get_cur_file()
            except IndexError: 
                # If there isn't another file and no 
                # '\n' character, return the data as-is
                return Data
            
            assert not nRemainder
            assert nFile != File
            Data += nFile.readline()
        return Data
        
    def seek(self, pos):
        # TODO: what about relative seeking?
        self.Pos = pos
    
    def tell(self):
        return self.Pos
        
    def read(self, amount):
        # A read() operation in a 2GB file probably isn't a good idea :-)
        # TODO: ADD SUPPORT FOR SPECIFIC AMOUNTS!
        raise NotImplementedError
        
    def write(self, data):
        File, Remainder = self.get_cur_file()
        Len = len(data)
        assert self.Pos == self.Size, \
            "Pos should equal size for large file access (Pos: %s; Size: %s)" % (self.Pos, self.Size)
        
        if Len+Remainder > MAX_SIZE:
            # Split to the current and open a new 
            # file, appending the remainder to it
            SlicePoint = (Len+Remainder)-MAX_SIZE
            File.write(data[:SlicePoint])
            nFile = self.open_new_file()
            nFile.write(data[SlicePoint:])
        else:
            File.write(data)
        self.Pos += Len
        self.Size += Len

#def large_file(*args):
#    return open(*args) # HACK!
