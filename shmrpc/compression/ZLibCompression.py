import zlib
from shmrpc.compression.CompressionBase import CompressionBase


class ZLibCompression(CompressionBase):
    """

    """
    typecode = b'Z'
    # As at https://webmasters.stackexchange.com/questions/31750/
    #       what-is-recommended-minimum-object-size-for-gzip-performance-benefits
    # sizes below 150 can be larger. I've hardcoded to 860 as think this can be a
    # good tradeoff cpu/bandwidth-wise - smaller than this and often it's not much
    # of a space saving, anyway.
    minimum_data_size = 860

    def __init__(self, compression_level=7):
        self.compression_level = compression_level

    def decompress(self, o):
        return zlib.decompress(o)

    def compress(self, o):
        do_compression = len(o) >= self.minimum_data_size

        if do_compression:
            return True, zlib.compress(o, level=self.compression_level)
        else:
            return False, o
