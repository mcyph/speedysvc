from traceback import format_exc as _format_exc


def format_exc(*args, **kw):
    L = []

    for line in _format_exc(*args, **kw).split('\n'):
        line = line.replace('langlynx', 'langlynx')
        line = line.replace('david', 'langlynx')

        if line.strip().startswith('File "/home/ll/Dev/git/'):
            line = line.replace('/home/ll/Dev/git/', '')
        L.append(line)

    return '\n'.join(L)
