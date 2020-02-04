def conv_to_str(o):
    if isinstance(o, str):
        # Remove initial "u" chars before strings
        # if no Unicode in them if possible
        try:
            o = str(o)
        except:
            o = str(o)

    elif isinstance(o, (list, tuple)):
        is_tuple = isinstance(o, tuple)
        o = [conv_to_str(i) for i in o]

        if is_tuple:
            o = tuple(o)

    elif isinstance(o, dict):
        for k in o:
            o[k] = conv_to_str(o[k])
    return o
