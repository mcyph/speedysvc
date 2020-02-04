from .WriteBase import WriteBase


class WriteIni(WriteBase):
    """
    Write Basic INI Files
    """
    def process_section(self, section, D):
        L = []
        for key in sorted(D, key=self.sort_key):
            value = D[key]
            assert not '=' in str(key)
            L.append('%s=%s' % (key, value))
        return '\n'.join(L)


write_D_ini = WriteIni().write_D
