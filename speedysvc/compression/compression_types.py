from speedysvc.compression.LZ4Compression import LZ4Compression
from speedysvc.compression.NullCompression import NullCompression
from speedysvc.compression.ZLibCompression import ZLibCompression
from speedysvc.compression.ZStdCompression import ZStdCompression
from speedysvc.compression.SnappyCompression import SnappyCompression


null_compression = NullCompression()
snappy_compression = SnappyCompression()
zlib_compression = ZLibCompression()
zstd_compression = ZStdCompression()
lz4_compression = LZ4Compression()

__LCompressors = [
    null_compression,
    snappy_compression,
    zlib_compression,
    zstd_compression,
    lz4_compression,
]

__DByCode = {}
for __compressor in __LCompressors:
    assert not __compressor.typecode in __DByCode, \
        __compressor.typecode
    __DByCode[__compressor.typecode] = __compressor


def get_by_type_code(code):
    return __DByCode[code]

