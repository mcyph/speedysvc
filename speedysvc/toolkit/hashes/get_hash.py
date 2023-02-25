from .fast_hash import fast_hash

SIgnore = {
    str, str, int, int, float, None
}


def get_hashable_types(obj):
    t = type(obj)

    if t in (list, tuple):
        # Convert lists to tuples
        rtn_list = []
        for i in obj:
            rtn_list.append(get_hashable_types(i))
        obj = tuple(rtn_list)

    elif t == dict:
        # Convert dicts to tuples
        rtn_list = []
        for k in obj:
            rtn_list.append((k, get_hashable_types(obj[k])))
        rtn_list.sort()
        obj = ('~~', tuple(rtn_list))
    
    elif t in SIgnore or obj is None:
        # Numeric or string/unicode? 
        # It's immutable, so ignore it!
        #try: obj = obj.decode('ascii', 'ignore')
        #except: pass
        pass
    
    else: 
        raise Exception("Type can't be hashed: %s (type: %s)" % (obj, type(obj)))

    return obj


def get_hash(obj):
    # Convert dict->sorted tuple
    # Convert list->tuple
    # and return the hash of Object
    obj = get_hashable_types(obj)
    return fast_hash(repr(obj))
