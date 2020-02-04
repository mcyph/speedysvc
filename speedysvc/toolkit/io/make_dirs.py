from os import makedirs
from os.path import exists, isdir


def make_dirs(dir_):
    #print 'EXISTS:', dir_, exists(dir_)
    exists_ = exists(dir_)

    if exists_ and not isdir(dir_):
        raise Exception('"%s" exists but isn\'t a directory!')
    elif not exists_:
        makedirs(dir_)
