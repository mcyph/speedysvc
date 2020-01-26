from .surrogates import w_ord


def is_char_hanzi(s):
    ord_ = w_ord(s)
    
    if ord_ >= 0x4E00 and ord_ <= 0x9FFF: 
        return 1
    elif ord_ >= 0x3400 and ord_ <= 0x4DBF: 
        return 1
    return 0


def is_hanzi(s):
    # TODO: REMOVE THE SEARCH LOGIC BELOW!
    
    # A basic check for whether a sentence uses all chinese characters
    # NOTE: It DOESN'T check compatibility or wide ranges!
    # TODO: SUPPORT COMMAS/FULL STOPS ETC?
    if len(s) < 4: 
        # HACK: Chances are <4 characters aren't sentences, so 
        # look up using the "Similar" fallback
        return False
    elif len(s) > 10:
        # For longer sentences, always return True for e.g. Thai
        return True
    
    hanzi_num = 0
    for char in s:
        ord_ = w_ord(char)
        
        if ord_ >= 0x4E00 and ord_ <= 0x9FFF: 
            hanzi_num += 1
        elif ord_ >= 0x3400 and ord_ <= 0x4DBF: 
            hanzi_num += 1
        elif not char.strip(): 
            hanzi_num += 1 # HACK!
        else: 
            pass
    
    if hanzi_num == len(s): 
        # If entirely hanzi_num, return True
        return 1
    elif hanzi_num > 3:
        # Kana/Kanji mix? If 3+ characters, chances are it's a sentence
        return 1
    else: 
        # Otherwise, use "auto" mode with spellchecking etc :-P
        return 0


def is_all_hanzi(s):
    if not s: 
        return False
    
    for char in s:
        ord_ = w_ord(char)
        
        if ord_ >= 0x4E00 and ord_ <= 0x9FFF: 
            pass
        elif ord_ >= 0x3400 and ord_ <= 0x4DBF: 
            pass
        else: 
            return 0
    return 1


def contains_hanzi(s):
    for char in s:
        ord_ = w_ord(char)
        
        if ord_ >= 0x4E00 and ord_ <= 0x9FFF: 
            return 1
        elif ord_ >= 0x3400 and ord_ <= 0x4DBF: 
            return 1
    return 0
