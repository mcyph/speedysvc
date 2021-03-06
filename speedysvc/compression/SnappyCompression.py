try:
    import snappy
except ImportError:
    snappy = None
from speedysvc.compression.CompressionBase import CompressionBase


_PACKAGE_ERROR = "The python-snappy package must be installed for snappy support to be available!"


class SnappyCompression(CompressionBase):
    """

    """
    typecode = b'S'
    # 860 seems a good minimum, as space savings below that seem to
    # often be minimal (and if choosing snappy over zlib, chances are
    # CPU is prioritised over space, anyway)
    minimum_data_size = 860

    def decompress(self, o):
        if not snappy:
            raise ImportError(_PACKAGE_ERROR)
        return snappy.decompress(o)

    def compress(self, o):
        if not snappy:
            raise ImportError(_PACKAGE_ERROR)
        do_compression = len(o) >= self.minimum_data_size

        if do_compression:
            return True, snappy.compress(o)
        else:
            return False, o
