from .get_dir_size import get_dir_size

cache_dict = {}
def cached_get_dir_size(folder):
    if not folder in cache_dict:
        cache_dict[folder] = get_dir_size(folder)
    return cache_dict[folder]

