def get_hex_point(ord_):
    # Get a unicode codepoint in format 0xXXXX 
    # or 0xXXXXXXXX from a codepoint ordinal
    hex_ = hex(int(ord_))[2:] # Chop off the '0x'
    hex_ = pad_hex(hex_)
    return '0x%s' % hex_.upper()


def get_uni_point(ord_):
    # Get a unicode codepoint in format U+XXXX 
    # or U+XXXXXXXX from a codepoint ordinal
    hex_ = hex(int(ord_))[2:] # Chop off the '0x'
    hex_ = pad_hex(hex_)
    return 'U+%s' % hex_.upper()


def pad_hex(hex_):
    # Pad hex to XXXX or XXXXXXXX for wide codepoints
    while 1:
        if len(hex_) in (4, 8):
            break
        elif len(hex_) > 8:
            raise Exception("Invalid hex_ Codepoint: %s" % hex_)
        hex_ = '0'+hex_
    return hex_


#print get_hex_point(5555)
#print get_hex_point(55555555)
#print get_uni_point(5555)
#print get_uni_point(55555555)
