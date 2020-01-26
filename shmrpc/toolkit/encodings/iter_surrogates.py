# -*- coding: utf-8 -*-


def iter_surrogates(s):
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
                return # HACK!
                #raise ValueError("Bad pair: string ends after %r" % i)
            
            if '\udc00' <= j < '\ue000':
                yield i + j
            elif False:
                raise ValueError("Bad pair: %r (bad second half)" % (i+j))
        
        elif '\udc00' <= i < '\ue000' and False: # HACK!
                raise ValueError("Bad pair: %r (no first half)" % i)
        
        else:
            yield i
