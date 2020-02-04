from os.path import split


def get_L_dirs(path):
    L = split_dir(path)
    return ['/'.join(L[:i]).replace('\\', '/').replace('//', '/')
            for i in range(1, len(L)+1)]


def split_dir(path):
    L = []
    while 1:
        path, folder = split(path)

        if folder != "":
            L.append(folder)
        else:
            if path != "":
                L.append(path)
            break

    L.reverse()
    return L


if __name__ == '__main__':
    from os import getcwdu
    print(get_L_dirs(getcwdu()))
