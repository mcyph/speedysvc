from network_tools.compression.CompressionBase import CompressionBase


class NullCompression(CompressionBase):
    """
    A basic stub class which doesn't compress/decompress - least cpu
    """
    def decompress(self, o):
        return o

    def compress(self, o):
        return o
