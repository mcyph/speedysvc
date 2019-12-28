from os import listdir

DUni = {}
DStr = {}


def cached_listdir(s):
    if isinstance(s, str):
        if not s in DUni:
            DUni[s] = listdir(s)
        return DUni[s]
    else:
        if not s in DStr:
            DStr[s] = listdir(s)
        return DStr[s]


