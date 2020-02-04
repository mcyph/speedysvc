from .ReadBase import ReadBase


class ReadHtmlIni(ReadBase):
    """
    Read HTML/Text INI Files
    """
    def process_section(self, section, data):
        """
        Reads .htmlini files which are just
        basic string keys/multiline values, e.g.

        [my section]
        the <b>quick</b> brown fox

        -> {'my section': 'the <b>quick</b> brown fox'}
        """
        return data


read_D_html_ini = ReadHtmlIni().read_D
