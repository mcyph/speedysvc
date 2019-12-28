from glob import glob

DUni = {}
DStr = {}


def cached_glob(s):
    if isinstance(s, str):
        if not s in DUni:
            DUni[s] = glob(s)
        return DUni[s]
    else:
        if not s in DStr:
            DStr[s] = glob(s)
        return DStr[s]

