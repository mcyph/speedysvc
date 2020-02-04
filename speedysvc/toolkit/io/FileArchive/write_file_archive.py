from array import array
from ..hashes.fast_hash import fast_hash


def write_file_archive(base_dir, LFiles, output_prefix):
    """
    Writes a basic file "archive" (of sorts), indexed by
    part of an MD5 hash (so no file listings are possible)

    The reason why this is useful is, the sound archives
    from Schtooka et al can have 1000s of files, and it
    can be inefficient/difficult managing such a large
    number when copying from one location to another etc
    on many filesystems.
    """
    LFiles = list(LFiles)
    LFiles.sort(key=lambda x: fast_hash(x))

    LFilenameHashes = array('Q')
    LSeek = array('Q')

    with open(f'{output_prefix}_data.bin', 'wb') as f_data:
        with open(
            f'{output_prefix}_listing.txt', 'w', encoding='utf-8'
        ) as f_listing:

            for fnam in LFiles:
                seek = f_data.tell()
                LFilenameHashes.append(fast_hash(fnam))
                LSeek.append(seek)

                with open('%s/%s' % (base_dir, fnam), 'rb') as f:
                    f_data.write(f.read())

                assert not ':' in fnam
                assert not '\n' in fnam

                amount = f_data.tell()-seek
                f_listing.write(f'{fnam}:{seek}:{amount}')

            LSeek.append(f_data.tell())

    with open(f'{output_prefix}_filenames.bin', 'wb') as f_filenamehashes:
        LFilenameHashes.tofile(f_filenamehashes)

    with open(f'{output_prefix}_seek.bin', 'wb') as f_seek:
        LSeek.tofile(f_seek)


