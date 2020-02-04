from io import BytesIO
from os import SEEK_END


class WriteStrArray:
    def __init__(self):
        self.typecode = 'u' # HACK!
        self.itemsize = 1 # HACK!
        self.f = BytesIO()

    def __len__(self):
        self.f.seek(0, SEEK_END)
        #print 'STR LEN:', self.f.tell()
        return self.f.tell()

    def extend(self, value):
        a = value.encode('utf-8')
        self.f.write(a)
        return len(a)

    def append(self, value):
        a = value.encode('utf-8')
        self.f.write(a)
        return len(a)

    def tofile(self, f):
        self.f.seek(0)

        while 1:
            data = self.f.read(1024)
            if not data:
                break
            f.write(data)
