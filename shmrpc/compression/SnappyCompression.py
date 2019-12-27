import snappy
from shmrpc.compression.CompressionBase import CompressionBase


class SnappyCompression(CompressionBase):
    """

    """
    def decompress(self, o):
        return snappy.decompress(o)

    def compress(self, o):
        return snappy.compress(o)
