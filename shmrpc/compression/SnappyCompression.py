import snappy
from shmrpc.compression.CompressionBase import CompressionBase


class SnappyCompression(CompressionBase):
    """

    """
    typecode = b'S'
    # 860 seems a good minimum, as space savings below that seem to
    # often be minimal (and if choosing snappy over zlib, chances are
    # CPU is prioritised over space, anyway)
    minimum_data_size = 860

    def decompress(self, o):
        return snappy.decompress(o)

    def compress(self, o):
        do_compression = len(o) >= self.minimum_data_size

        if do_compression:
            return True, snappy.compress(o)
        else:
            return False, o
