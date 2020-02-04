from .WriteBase import WriteBase, conv_to_str

from .conv_to_str import conv_to_str


class WritePyIni(WriteBase):
    """
    Write "Python" INI Files
    """
    use_colons = True

    def process_section(self, section, D):
        L = []
        for key in sorted(D, key=self.sort_key):
            value = conv_to_str(D[key])
            L.append('    %s = %s' % (key, repr(value)))
        return '\n'.join(L)


write_D_pyini = WritePyIni().write_D
