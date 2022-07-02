try:
    import zstd
except ImportError:
    zstd = None
from speedysvc.compression.CompressionBase import CompressionBase


_PACKAGE_ERROR = "The zstd package must be installed for Zstandard compression support to be available!"


class ZStdCompression(CompressionBase):
    typecode = b'T'
    # 860 seems a good minimum, as space savings below that seem to
    # often be minimal (and if choosing zstd over zlib, chances are
    # CPU is prioritised over space, anyway)
    minimum_data_size = 860

    def decompress(self, o):
        if not zstd:
            raise ImportError(_PACKAGE_ERROR)
        return zstd.decompress(o)

    def compress(self, o):
        if not zstd:
            raise ImportError(_PACKAGE_ERROR)
        do_compression = len(o) >= self.minimum_data_size

        if do_compression:
            return True, zstd.compress(o)
        else:
            return False, o
