from .fast_hash import fast_hash

SIgnore = {
    str, str, int, int, float, None
}


def get_hashable_types(obj):
    t = type(obj)

    if t in (list, tuple):
        # Convert lists to tuples
        return_list = []
        for i in obj:
            return_list.append(get_hashable_types(i))
        obj = tuple(return_list)

    elif t == dict:
        # Convert dicts to tuples
        return_list = []
        for k in obj:
            return_list.append((k, get_hashable_types(obj[k])))
        return_list.sort()
        obj = ('~~', tuple(return_list))
    
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
