from .ReadBase import ReadBase


class ReadIni(ReadBase):
    """
    Read Basic INI Files
    """
    def process_section(self, section, data):
        """
        Reads a simple INI file with string keys/values
        "=" characters in keys aren't allowed!
        Newlines also aren't supported in keys/values

        "#" characters only at the start of lines are
        interpreted as comments

        [section]
        # my comment
        key = value

        -> {'section': {'key': 'value'}}
        """
        DRtn = {}
        for line in data.split('\n'):
            line = line.strip()

            if line.startswith('#'):
                continue
            elif not '=' in line:
                continue

            key, _, value = line.partition('=')
            DRtn[key.strip()] = value.strip()
        return DRtn


read_D_ini = ReadIni().read_D
