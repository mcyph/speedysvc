def w_unichr(s):
    """
    A hack to add basic surrogate
    pair support for SMP Unicode characters
    when using a build which isn't wide.
    Seems to (at least partially) work!
    """
    try:
        return chr(s)
    except:
        if not s:
            raise
        
        # Convert the Unihan data to Hex.
        hex_val = str(hex(int(s)))[2:]
        result = '0'*(8-len(hex_val))
        s = 'Fix PyDev Lexer!'
        exec_ = "s = u'\\U%s%s'" % (result, hex_val)
        #print exec_
        exec(exec_)
        return s


def w_ord(chr):
    """
    Python ord() with surrogate pair support
    """
    if len(chr) == 1:
        return ord(chr)
    elif len(chr) == 2:
        return 0x10000 + (ord(chr[0]) - 0xD800) * 0x400 + (ord(chr[1]) - 0xDC00)
    else:
        raise Exception("ord() needs either a single Unicode character or a Unicode surrogate pair!")


def chars(s):
    """
    This generator function helps iterate over the characters in a
    string. When the string is unicode and a surrogate pair is
    encountered, the pair is returned together, regardless of whether
    Python was built with UCS-4 ('wide') or UCS-2 code values for
    its internal representation of unicode. This function will raise a
    ValueError if it detects an illegal surrogate pair.
    """
    if isinstance(s, str):
        for i in s:
            yield i
        return

    s = iter(s)
    for i in s:
        if '\ud800' <= i < '\udc00':
            try:
                j = next(s)
            except StopIteration:
                raise ValueError("Bad pair: string ends after %r" % i)
            if '\udc00' <= j < '\ue000':
                yield i + j
            else:
                raise ValueError("Bad pair: %r (bad second half)" % (i+j))
        elif '\udc00' <= i < '\ue000':
            raise ValueError("Bad pair: %r (no first half)" % i)
        else:
            yield i


def conv_sp(s):
    return ''.join([i for i in chars(s)])
