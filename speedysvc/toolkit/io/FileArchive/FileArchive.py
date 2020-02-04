from os.path import getsize
from struct import calcsize
from _thread import allocate_lock
from bisect import bisect_left
from ..arrays.array_read.NumArray import NumArray


class DFileArchive:
    def __init__(self, output_prefix):
        seek_path = f'{output_prefix}_seek.bin'
        filenames_path = f'{output_prefix}_filenames.bin'

        self.LSeek = NumArray(
            dtype='Q', buffer=open(seek_path, 'rb'),
            offset=0, shape=(getsize(seek_path)/calcsize('Q'),)
        )
        self.LFilenameHashes = NumArray(
            dtype='Q', buffer=open(filenames_path, 'rb'),
            offset=0, shape=(getsize(filenames_path)/calcsize('Q'),)
        )
        self.f_data = open(f'{output_prefix}_data.bin', 'rb')

        self.lock = allocate_lock()

    def __iter__(self):
        """
        TODO: Go through the file listing data!
        """
        raise NotImplementedError

    def __getitem__(self, item):
        seek_pos = bisect_left(self.LSeek, item)
        if self.LSeek[seek_pos] != item:
            raise KeyError(item)

        seek = self.LSeek[seek_pos]
        amount = self.LSeek[seek_pos+1]-seek

        with self.lock:
            self.f_data.seek(seek)
            return self.f_data.read(amount)
