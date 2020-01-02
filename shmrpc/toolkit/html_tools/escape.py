def esc_word_disp(s):
    s = s.replace('<', '&#60;')
    s = s.replace('>', '&#62;')
    return s


def dec_word_disp(s):
    s = s.replace('&#60;', '<')
    s = s.replace('&#62;', '>')
    return s


def esc_q(s):
    # Escape <param="%s">
    s = s.replace('&', '&amp;') # CHECK ME!
    s = s.replace('"', '&quot;') # ' -> &quot;
    
    # Not stricly speaking needed, but reduces 
    # the risk in the event of a vulnerability
    s = s.replace('<', '&#60;')
    s = s.replace('>', '&#62;')
    return s


def esc_p(s):
    # Escape <param='%s'>
    s = s.replace('&', '&amp;') # CHECK ME!
    s = s.replace("'", '&#39;') # ' -> &#39;
    
    # Not stricly speaking needed, but reduces 
    # the risk in the event of a vulnerability
    s = s.replace('<', '&#60;')
    s = s.replace('>', '&#62;')
    return s


def esc_qp(s):
    # Escape <onclick="blah('%s')">
    s = s.replace('&', '&amp;') # CHECK ME!
    s = s.replace('"', '&quot;') # Escape XML (" -> &quot;)
    s = s.replace('\\', '\\\\') # \ -> \\
    s = s.replace("'", r"\'") # Escape JS (' -> \')
    s = s.replace('\n', r'\n') # \n -> \\n
    
    # Not stricly speaking needed, but reduces 
    # the risk in the event of a vulnerability
    s = s.replace('<', '&#60;')
    s = s.replace('>', '&#62;')
    return s


def esc_pq(s):
    # Escape <onclick='blah("%s")'>
    s = s.replace('&', '&amp;') # CHECK ME!
    s = s.replace("'", '&#39;') # Escape XML (' -> &#39;)
    s = s.replace('\\', '\\\\') # \ -> \\
    s = s.replace('"', r'\"') # Escape JS (" -> \")
    s = s.replace('\n', r'\n') # \n -> \\n
    
    # Not stricly speaking needed, but reduces 
    # the risk in the event of a vulnerability
    s = s.replace('<', '&#60;')
    s = s.replace('>', '&#62;')
    return s


def E(s, esc_whitespace=False, strip=True, nls=True):
    # Escape the HTML.
    #s = markdown.Markdown(s, safe_mode=True)
    #return s.toString().strip('\r\n')
    if len(s) != 1 and strip: 
        s = s.strip('\r\n').strip()
    
    s = s.replace('&', '&amp;') # CHECK ME!
    
    if esc_whitespace: 
        s = s.replace(' ', '&#32;')
    
    s = s.replace('\t', '&#09;')
    #s = s.replace(' ', '&#32;') # Non-breaking space
    s = s.replace('<', '&#60;')
    s = s.replace('>', '&#62;')
    
    if nls: 
        s = s.replace('\n', '<BR />')
    
    #s = s.replace("'", '&#39;')
    s = s.replace('"', '&quot;')
    return s
