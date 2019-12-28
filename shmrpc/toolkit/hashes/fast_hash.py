import hashlib


def fast_hash(s):
    """
    Fast hash unicode string `s`
    """
    md5 = hashlib.md5()
    md5.update(s.encode('utf-8'))
    digest = md5.hexdigest()
    # This uses the first 63+last 63 md5 bits and
    # xors them to (hopefully) reduce collisions

    # Note that I'm using 63 bits rather than 64
    # to make it fit into signed ints(!)

    number = int(digest[1:16], 16) ^ int(digest[17:], 16)
    return number


if __name__ == '__main__':
    for x in range(1000000):
        fast_hash('basdsadsadsadas ds fds f dsf sd fsd fsd f sdf sd')
