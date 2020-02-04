from html.entities import name2codepoint, codepoint2name
from ..encodings.surrogates import w_unichr, w_ord

hex_ = '1234567890ABCDEF'
SHex = set(hex_+hex_.lower())


def is_hex(s):
    if not s: 
        return False
    
    for i in s: 
        if i not in SHex:
            return False
    
    return True


def unescape(s, LReescape=None):
    """
    Converts HTML character references into a unicode string to allow manipulation
    
    If LUnEscape is provided, then the positions of the escaped characters will be 
    added to allow turning the result back into HTML with reescape below, validating 
    the references and escaping all the rest
    
    This is needed to prevent browsers from stripping out e.g. &#32; (spaces) etc
    """
    re = LReescape != None
    
    L = []
    xx = 0
    yy = 0
    
    for xx, i_s in enumerate(s.split('&')):
        if xx:
            LSplit = i_s.split(';')
            if LSplit[0].lower() in name2codepoint:
                # A character reference, e.g. '&amp;'
                a = w_unichr(name2codepoint[LSplit[0].lower()])
                L.append(a+';'.join(LSplit[1:]))
                if re: 
                    LReescape.append((yy, a))
                
            elif LSplit[0] and LSplit[0][0]=='#' and LSplit[0][1:].isdigit():
                # A character number e.g. '&#52;'
                a = w_unichr(int(LSplit[0][1:]))
                L.append(a+';'.join(LSplit[1:]))
                if re: 
                    LReescape.append((yy, a))
                
            elif LSplit[0] and LSplit[0][0]=='#' and \
                 LSplit[0][1:2].lower()=='x' and \
                 is_hex(LSplit[0][2:]):
                
                # A hexadecimal encoded character
                a = w_unichr(int(LSplit[0][2:].lower(), 16)) # Hex -> base 16
                L.append(a+';'.join(LSplit[1:]))
                if re: 
                    LReescape.append((yy, a))
                
            else: 
                L.append('&%s' % ';'.join(LSplit))
        else: 
            L.append(i_s)
        
        xx += 1
        yy += len(L[-1])
    return ''.join(L)


def reescape(LReescape, s, escape_fn):
    """
    Re-escapes the output of unescape to HTML, ensuring e.g. &#32; 
    is turned back again and isn't stripped at a browser level
    Supports Unicode surrogate pairs if enabled in File.py
    """
    L = []
    prev = 0
    for x, c in LReescape:
        if x != prev:
            L.append(escape_fn(s[prev:x]))
        
        o = w_ord(c)
        if o in codepoint2name:
            # TODO: Only add for whitespace etc?
            L.append('&%s;' % codepoint2name[o])
        else: 
            L.append('&#%s;' % o)
        
        prev = x+len(c)
    L.append(escape_fn(s[prev:]))
    return ''.join(L)


if __name__ == '__main__':
    # All of these should output "javascript:alert('XSS')"
    # http://htmlpurifier.org/live/smoketests/xssAttacks.php
    print(unescape('&#0000106&#0000097&#0000118&#0000097&#0000115&#0000099&#0000114&#0000105&#0000112&#0000116&#0000058&#0000097&#0000108&#0000101&#0000114&#0000116&#0000040&#0000039&#0000088&#0000083&#0000083&#0000039&#0000041'))
    print(unescape('&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;&#97;&#108;&#101;&#114;&#116;&#40;&#39;&#88;&#83;&#83;&#39;&#41;'))
    print(unescape('&#x6A;&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53&#x27&#x29'))
