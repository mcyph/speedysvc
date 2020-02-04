from shmrpc.compression.CompressionBase import CompressionBase


class NullCompression(CompressionBase):
    """
    A basic stub class which doesn't compress/decompress - least cpu
    """
    typecode = b'N'
    minimum_data_size = 0

    def decompress(self, o):
        return o

    def compress(self, o):
        return True, o
