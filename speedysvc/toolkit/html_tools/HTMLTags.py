from re import compile, DOTALL
from ..html_tools.escape import esc_q

from .Unescape import unescape
from .SanitizeHTML import sanitize_html, SElms, SAttr, SURITypes


RE_END_OF_TAG = compile('\s*(>|$)')

DALPHA = {}
for i in 'abcdefghijklmnopqrstuvwxyz':
    DALPHA[i.lower()] = None
    DALPHA[i.upper()] = None


def get_tag_name(s, x=0):
    if s[x] != '<':
        # Not an HTML tag! 
        return None
    x += 1
    
    LTag = []
    while 1:
        if x > len(s)-1:
            # WARNING! 
            break
        
        c = s[x]
        if c.strip():
            if c == '>': 
                break
            elif c == '/' and LTag:
                break
            LTag.append(c)
        elif LTag: 
            break
        
        x += 1
    tag_name = ''.join(LTag).lower()
    return tag_name or None


def get_htm_tag(s, x=1):
    """
    See also http://htmlpurifier.org/live/smoketests/xssAttacks.php
    http://intertwingly.net/stories/2007/08/13/sanitize_lists.cgi
    http://wiki.whatwg.org/wiki/Sanitization_rules
    http://code.google.com/p/html5lib/wiki/UserDocumentation
    Returns [tag_name, xhtml, DTags, Index]
    """
    
    # First, get the tag name
    LTag = []
    tag_ended = False
    xhtml = False
    len_ = len(s)
    
    while 1:
        if x > len_-1: 
            # WARNING!
            break
        
        c = s[x]
        #print c
        if c.strip():
            if c == '/' and LTag:
                if RE_END_OF_TAG.match(s, pos=x+1):
                    xhtml = True
                break
            
            if c == '>': 
                tag_ended = True
                break
            
            if c != '<': # HACK!
                LTag.append(c)
        
        elif LTag: 
            break
        x += 1
    tag_name = ''.join(LTag).lower()
    
    D = {} # key: Value
    quotes = False # Quotes
    paranthesis = False # Paranthesis
    
    KEY = 0
    VALUE = 1
    WFV = 2

    mode = KEY
    
    key = ''
    value = ''
    len_ = len(s)

    while not tag_ended:
        if x > len_-1:
            # WARNING!
            break
        c = s[x]
        #print x, s[x], mode, key, value

        if paranthesis:
            end = s.find("'", x)
            end = len_ if end == -1 else end
            D[key] = s[x:end]

            x = end
            mode = KEY
            paranthesis = False
            key = value = ''


        elif quotes:
            end = s.find('"', x)
            end = len_ if end == -1 else end
            D[key] = s[x:end]

            x = end
            mode = KEY
            quotes = False
            key = value = ''


        elif mode == KEY:
            if c == '/':
                if RE_END_OF_TAG.match(s, pos=x+1):
                    # xhtml Tag
                    xhtml = True
            elif c == '>':
                # end Tag
                break
            elif c == '=':
                # start value
                mode = VALUE
            elif c.strip():
                # Continue key 
                key += c
            elif key: 
                # end key - waiting for value
                mode = WFV


        elif mode == WFV and c.strip():
            # Waiting for value
            # This allows mangled tags like "<img src = blah>" to be
            # processed if there's whitespace before the '=' sign,
            # and assigns "None" to the key if there's a new key without one,
            # allowing "<option selected value="blah">" to be parsed properly
            
            if c == '=':
                # start value
                mode = VALUE    
            elif c == '/':
                if RE_END_OF_TAG.match(s, pos=x+1):
                    # xhtml Tag
                    xhtml = True
            elif c == '>':
                # end Tag
                break
            elif c.strip():
                # A second key - append the previous as blank!
                D[key] = None # WARNING!
                mode = KEY
                key = c
                value = ''


        elif mode == VALUE:
            # start quotes/paranthesis
            if not c.strip() and not value:
                pass # 'blah =[ ]blah' HACK!
            elif c == '"':
                quotes = True
            elif c == "'":
                paranthesis = True
            
            elif c == '/':
                if RE_END_OF_TAG.match(s, pos=x+1):
                    xhtml = True # xhtml Tag
            elif c == '>':
                break # end Tag
            elif c.strip():
                value += c # Continue value
            else: 
                # end value
                mode = KEY
                if key: 
                    D[key] = value
                elif value: 
                    pass # WARNING!
                key = value = ''
        x += 1


    # Append the last key/value
    if key and mode in (KEY, WFV): 
        D[key] = None
    elif key and mode == VALUE: 
        D[key] = value


    for k in tuple(D.keys()):
        # Unescape &x; refs
        if D[k]:
            D[k] = unescape(D[k])

        # Only allow a-Z in keys!
        invalid = False
        for i in k:
            if i not in DALPHA:
                invalid = True

        if invalid:
            del D[k]

            #value = D[k]
            #del D[k]
            #nK = ''.join([i for i in k if i in DALPHA])
            #D[nK] = value

    #print tag_name, xhtml, D, x
    return tag_name, xhtml, D, x+1


def output_htm(tag_name, xhtml, D, 
               sanitize=True, output_tag=True):
    
    # First, sanitize the HTML tag
    if sanitize:
        # HACK! =============================================================
        tag_name, D = sanitize_html(tag_name, D, 
                                    SElms, SAttr, SURITypes)
        if not tag_name: 
            return '' # WARNING - Tag not allowed!
    
    # Output the tag
    return_list = []
    if output_tag: 
        return_list.append('<%s' % tag_name)
    
    for k in D:
        # Output escaped values
        #print k, D[k]

        if D[k] is not None:
            return_list.append(' %s="%s"' % (k, esc_q(D[k])))
        else:
            # HTML key without a value, e.g. "nowrap" in "td" elements
            return_list.append(' %s' % k)
    
    # Output the end of the tag
    if not output_tag: 
        if xhtml: 
            return_list.append(' /')
    else:
        if xhtml: 
            return_list.append(' />')
        else: 
            return_list.append('>')
    return ''.join(return_list)


if __name__ == '__main__':
    print('BLAH')
    tag_name, xhtml, D, x = get_htm_tag('<br/  myparam=\"blah blah blah blah blah\" />')
    print(tag_name, xhtml, D, x)

    tag_name, xhtml, D, x = get_htm_tag('<br/ / myparam/=\"blah blah blah blah blah\" >')
    print(tag_name, xhtml, D, x)

    #print output_htm(tag_name, xhtml, D,
    #    sanitize=True, output_tag=True)

    from timeit import timeit
    print(timeit(
        "get_htm_tag('<br/  myparam=\"blah blah blah blah blah\" />')",
        setup="from HTMLTags import get_htm_tag",
        number=1000000
    ))
