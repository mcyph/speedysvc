import snappy
from network_tools.compression.CompressionBase import CompressionBase


class SnappyCompression(CompressionBase):
    def decompress(self, o):
        return snappy.decompress(o)

    def compress(self, o):
        return snappy.compress(o)
