from html.entities import name2codepoint
from ..encodings.surrogates import w_unichr

# Get the whitespace characters
# OPEN ISSUE: Add non-breaking space, just for good measure? ====================================================
DNums = {0: ' ', 1: '\t', 2: '\r', 3: '\n'}
DChars = dict((x, y) for y, x in list(DNums.items()))
DNums2XML = {0: '&#32;', 1: '&#09;', 2: '&#13;', 3: '&#10;'}
DChars2XML = dict((DNums[i], DNums2XML[i]) for i in DNums2XML)

# For transliteration/the HTML output system (Flazzle specific)
DNums2CtrlChars = {0: '\x11', 1: '\x12', 2: '\x13', 3: '\x14'}

S = '1234567890ABCDEF'
DHex = {}
for i in S:
    DHex[i.lower()] = None
    DHex[i.upper()] = None
del S

    
def IsHex(S):
    if not S: return False
    for i in S: 
        if i not in DHex:
            return False
    return True


class CUnescape:
    def __init__(self, S, ignoreWS=False):
        # Converts HTML character references into a unicode string to allow manipulation
        #
        # If LUnescape is provided, then the positions of the escaped characters will be 
        # added to allow turning the result back into HTML with ReEscape below, validating 
        # the references and escaping all the rest
        # 
        # This is needed to prevent browsers from stripping out e.g. &#32; (spaces) etc
        
        self.S = S
        self.ignoreWS = ignoreWS
        self.L = self.process(ignoreWS)
        
    def process(self, ignoreWS):
        def getChar(c):
            if ignoreWS:
                return c
            else:
                if c in DChars:
                    return DChars[c]
                else: return c
        
        return_list = []
        L = self.S.split('&')
        xx = 0
        yy = 0
        for iS in L:
            if xx:
                LSplit = iS.split(';')
                if LSplit[0].lower() in name2codepoint:
                    # A character reference, e.g. '&amp;'
                    a = w_unichr(name2codepoint[LSplit[0].lower()])
                    return_list.append(getChar(a)) # TOKEN CHECK?
                    return_list.append(';'.join(LSplit[1:]))
                    
                elif LSplit[0] and LSplit[0][0] == '#' and LSplit[0][1:].isdigit():
                    # A character number e.g. '&#52;'
                    a = w_unichr(int(LSplit[0][1:]))
                    return_list.append(getChar(a))
                    return_list.append(';'.join(LSplit[1:]))
                    
                elif LSplit[0] and LSplit[0][0] == '#' and LSplit[0][1:2].lower() == 'x' and IsHex(LSplit[0][2:]):
                    # A hexadecimal encoded character
                    a = w_unichr(int(LSplit[0][2:].lower(), 16)) # Hex -> base 16
                    return_list.append(getChar(a))
                    return_list.append(';'.join(LSplit[1:]))
                    
                else: return_list.append('&%s' % ';'.join(LSplit))
            else: return_list.append(iS)
            xx += 1
            yy += len(return_list[-1])
        return return_list
        
    def map(self, charFn, intFn=None):
        # Go through each region in self.L, applying `charFn` to the 
        # unicode characters and `intFn` for characters like spaces 
        # etc which were explicitly inserted in HTML as e.g. &#32;
        # to prevent them from being stripped
        
        L = []
        for i in self.L:
            if type(i) == int:
                # Process explicit newlines/tabs/spaces etc
                # NOTE: If intFn is specified, it sends the character 
                # itself e,g, '\r' or ' ' as an argument
                if intFn: L.append(intFn(DNums[i]))
                else: L.append(DNums2XML[i])
            else:
                # Process other codes
                L.append(charFn(i))
        return ''.join(L)
        
    def getValue(self):
        # Convert back into HTML, preserving 
        # whitespace if self.ignoreWS is `False`
        L = []
        for i in self.L:
            if type(i) == int:
                L.append(DNums2XML[i])
            else:
                L.append(i)
        return ''.join(L)
        
    def __str__(self):
        return str(self.getValue())
    
    def __unicode__(self):
        return str(self.getValue())


def Unescape(S):
    # Get the string value from escaped HTML `S`, ignoring 
    # explicit whitespace like tabs/spaces etc
    IUnescape = CUnescape(S, ignoreWS=True)
    return ''.join(IUnescape.L)
