from .ReadBase import ReadBase


class ReadPyIni(ReadBase):
    """
    Read "Python" INI Files
    """
    def process_section(self__, section__, txt__):
        """
        Convert the variables in evaluable `txt_` to a dict

        Read a .pyini file (section contents
        have an optional single indent), i.e.

        ['section 1', 'section2']
        my_variable = range(2)

        -> {'section 1': {'my_variable': [0, 1, 2]},
            'section 2': {'my_variable': [0, 1, 2]}}

        (any python expression is allowed)
        """
        exec(self__.remove_indent(txt__).replace('\r\n', '\n'))
        D = dict(locals())
        del D['txt__'] # HACK!
        del D['section__'] # HACK!
        del D['self__'] # HACK!
        return D

    def remove_indent(self, txt_):
        """
        Make it so that a single indentation is possible
        for readability, but don't require it
        """
        L = []
        txt_ = txt_.replace('\t', ' '*4)

        for line in txt_.split('\n'):
            if not line[:4].strip():
                line = line[4:]
            L.append(line)

        return '\n'.join(L)


read_D_pyini = ReadPyIni().read_D
