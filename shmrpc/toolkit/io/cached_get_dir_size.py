from .get_dir_size import get_dir_size

DCache = {}
def cached_get_dir_size(folder):
    if not folder in DCache:
        DCache[folder] = get_dir_size(folder)
    return DCache[folder]

