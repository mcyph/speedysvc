from .WriteBase import WriteBase


class WriteHtmlIni(WriteBase):
    """
    Write HTML/Text INI Files
    """
    def process_section(self, section, D):
        L = []
        for sub_key in sorted(D, key=self.sort_key):
            L.append('%s\n' % D[sub_key])
        return '\n'.join(L)


write_D_html_ini = WriteHtmlIni().write_D
