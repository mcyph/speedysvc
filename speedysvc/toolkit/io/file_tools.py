
import codecs


def file_iter(path, encoding='utf-8', errors='strict'):
    """
    Iterate through a file's contents with the
    benefits of `with` with less indentation
    """
    with open(path, 'r', encoding=encoding, errors=errors) as f:
        for line in f:
            yield line


def file_read(path, encoding='utf-8', errors='strict'):
    """
    Return a file's contents as a string
    """
    with open(path, 'r', encoding=encoding, errors=errors) as f:
        return f.read()


def file_write(path, txt, encoding='utf-8'):
    """
    Update a file's contents with a string
    """
    with open(path, 'w', encoding=encoding) as f:
        f.write(txt)
