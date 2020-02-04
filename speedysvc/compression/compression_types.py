from speedysvc.compression.SnappyCompression import SnappyCompression
from speedysvc.compression.NullCompression import NullCompression
from speedysvc.compression.ZLibCompression import ZLibCompression


null_compression = NullCompression()
snappy_compression = SnappyCompression()
zlib_compression = ZLibCompression()

__LCompressors = [
    null_compression,
    snappy_compression,
    zlib_compression
]

__DByCode = {}
for __compressor in __LCompressors:
    __DByCode[__compressor.typecode] = __compressor


def get_by_type_code(code):
    return __DByCode[code]

