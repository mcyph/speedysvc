from json import loads


def read_json(f, L):
    """
    Read JSON data from `f`
    """
    #print L
    seek, amount = L
    f.seek(seek)
    data = f.read(amount).decode('utf-8')
    return loads(data)
