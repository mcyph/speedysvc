from json import dumps


def write_json(f, data):
    """
    Write JSON data to `f` and return the info needed to later read
    the data with `read_json`
    """
    seek = f.tell()
    f.write(dumps(data).encode('utf-8'))
    amount = f.tell() - seek

    return [seek, amount]
