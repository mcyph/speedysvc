import _thread
from glob import glob, iglob
from os import stat, listdir
from os.path import normpath, exists, sep, join, isfile, isdir
from time import sleep
from json import loads, dumps
from collections import namedtuple


StatObj = namedtuple('StatObj', [
    'st_mode', # protection bits.
    'st_ino', # inode number.
    'st_dev', # device.
    'st_nlink', # number of hard links.
    'st_uid', # user id of owner.
    'st_gid', # group id of owner.
    'st_size', # size of file, in bytes.
    'st_atime', # time of most recent access.
    'st_mtime', # time of most recent content modification.
    'st_ctime', # time of most recent metadata change.
])


class CachedIO:
    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.changed = False
        self.lock = _thread.allocate_lock()

        if exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                D = loads(f.read())

                self.DStat = D['DStat']
                self.DDirSize = D['DDirSize']
                self.DListDir = D['DListDir']
                self.DGlob = D['DGlob']
                self.DIGlob = D['DIGlob']
                self.DExists = D['DExists']
                self.DIsDir = D['DIsDir']
        else:
            self.invalidate_all()

        _thread.start_new_thread(self.__monitor_for_changes, ())

    def __monitor_for_changes(self):
        while 1:
            if self.changed:
                self.__write()
            sleep(3)

    def __write(self):
        with self.lock:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                f.write(dumps({
                    'DStat': self.DStat,
                    'DDirSize': self.DDirSize,
                    'DListDir': self.DListDir,
                    'DGlob': self.DGlob,
                    'DIGlob': self.DIGlob,
                    'DExists': self.DExists,
                    'DIsDir': self.DIsDir
                }))

            self.changed = False

    def invalidate_all(self):
        self.DStat = {}
        self.DDirSize = {}
        self.DListDir = {}
        self.DGlob = {}
        self.DIGlob = {}
        self.DExists = {}
        self.DIsDir = {}

        self.changed = True

    #====================================================================#
    #                             Stat-Related                           #
    #====================================================================#

    def stat(self, path):
        path = normpath(path)

        if not path in self.DStat:
            with self.lock:
                self.DStat[path] = tuple(stat(path))
                self.changed = True

        return StatObj(*self.DStat[path])

    def get_size(self, path):
        return self.stat(path).st_size

    def get_modified(self, path):
        return self.stat(path).st_mtime

    def invalidate_stat_dir(self, dir_):
        dir_ = normpath(dir_).rstrip('/\\')

        with self.lock:
            LDel = []
            for path in self.DStat:
                if path.startswith(dir_+sep):
                    LDel.append(path)

            for i in LDel:
                del self.DStat[i]
            self.changed = True

    #====================================================================#
    #                            Exists Cache                            #
    #====================================================================#

    def exists(self, path):
        path = normpath(path)

        if not path in self.DExists:
            with self.lock:
                self.DExists[path] = exists(path)
                self.changed = True

        return self.DExists[path]

    #====================================================================#
    #                            Is Folder Cache                            #
    #====================================================================#

    def isdir(self, path):
        path = normpath(path)

        if not path in self.DIsDir:
            with self.lock:
                self.DIsDir[path] = isdir(path)
                self.changed = True

        return self.DIsDir[path]

    #====================================================================#
    #                          Folder Size Cache                         #
    #====================================================================#

    def get_dir_size(self, folder):
        folder = normpath(folder)

        if folder in self.DDirSize:
            return self.DDirSize[folder]

        total_size = self.get_size(folder)

        for item in self.listdir(folder):
            item_path = join(folder, item)

            if isfile(item_path):
                total_size += self.get_size(item_path)
            elif self.isdir(item_path):
                total_size += self.get_dir_size(item_path)

        with self.lock:
            self.DDirSize[folder] = total_size
            self.changed = True

        return total_size

    #====================================================================#
    #                            Listdir Cache                           #
    #====================================================================#

    def listdir(self, dir_):
        dir_ = normpath(dir_)

        if not dir_ in self.DListDir:
            with self.lock:
                self.DListDir[dir_] = listdir(dir_)
                self.changed = True

        return self.DListDir[dir_]

    #====================================================================#
    #                             Glob Cache                             #
    #====================================================================#

    def glob(self, pattern):
        if not pattern in self.DGlob:
            with self.lock:
                self.DGlob[pattern] = glob(pattern)
                self.changed = True

        return self.DGlob[pattern]

    def iglob(self, pattern):
        if not pattern in self.DIGlob:
            with self.lock:
                self.DIGlob[pattern] = glob(pattern)
                self.changed = True

        return self.DIGlob[pattern]

