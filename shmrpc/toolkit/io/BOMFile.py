import codecs


class BOMFile:
    def __init__(self, path):
        # A UTF-8 file which includes the BOM (codecs.open doesn't)
        # so that SciTE etc detect the encoding correctly
        self.f = open(path, 'wb')
        self.f.write(codecs.BOM_UTF8)
        
    def write(self, data):
        self.f.write(data.encode('utf-8'))
    
    def close(self):
        self.f.close()
