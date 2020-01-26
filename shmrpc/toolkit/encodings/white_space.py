# -*- coding: utf-8 -*-
import copy
import string

# Tab, Newline, Something, Something, Form Feed
tWHITESPACE = '\u0000\u0001\u0003\u0004\u0005\u0006\u0007\u0008\u0009\u000A\
\u000B\u000C\u000D\u000E\u000F\u001A\u001B\u001C\u001D\u001E\u001F\t\n\x0b\x0c\
\r \u0009\u000A\u000B\u000C\u000D\u3000\u205F\u202F\u2029\u2028 \u00A0 \u1680 \
\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A'
WHITESPACE = {} # Convert to a dictionary. Looking up by hash is much faster than using "in (string)" :-)
for Char in tWHITESPACE: WHITESPACE[Char] = None
JWHITESPACE = copy.deepcopy(WHITESPACE)
jWHITESPACE = ' ()[]&;!.#\v!@~`^&*+=/"\'/.,|�1234567890'+string.ascii_letters
for Char in jWHITESPACE: JWHITESPACE[Char] = None
HTMLWHITESPACE = {'\t': None, ' ': None, '\n': None, '\u200B': None}
