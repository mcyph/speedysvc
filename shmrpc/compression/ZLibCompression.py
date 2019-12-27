import zlib
from shmrpc.compression.CompressionBase import CompressionBase


class ZlibCompression(CompressionBase):
    """

    """
    def __init__(self, compression_level=7):
        self.compression_level = compression_level

    def decompress(self, o):
        return zlib.compress(o, level=self.compression_level)

    def compress(self, o):
        return zlib.decompress(o)
