try:
    import lz4
except ImportError:
    lz4 = None
from speedysvc.compression.CompressionBase import CompressionBase


_PACKAGE_ERROR = "The lz4 package must be installed for lz4 support to be available!"


class LZ4Compression(CompressionBase):
    """

    """
    typecode = b'L'
    # 860 seems a good minimum, as space savings below that seem to
    # often be minimal (and if choosing snappy over zlib, chances are
    # CPU is prioritised over space, anyway)
    minimum_data_size = 860

    def decompress(self, o):
        if not lz4:
            raise ImportError(_PACKAGE_ERROR)
        return lz4.decompress(o)

    def compress(self, o):
        if not lz4:
            raise ImportError(_PACKAGE_ERROR)
        do_compression = len(o) >= self.minimum_data_size

        if do_compression:
            return True, lz4.compress(o)
        else:
            return False, o
