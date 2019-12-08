from network_tools.compression.CompressionBase import CompressionBase


class NullCompression(CompressionBase):
    def decompress(self, o):
        return o

    def compress(self, o):
        return o
