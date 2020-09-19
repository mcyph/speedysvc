import mmap


memory1 = mmap.mmap(-1,
                   length=8192,
                   tagname='blah',
                   access=mmap.ACCESS_WRITE)
if any(memory1[:]):
    raise Exception("Memory should be all zeroes!")

memory2 = mmap.mmap(-1,
                   length=8192,
                   tagname='blah',
                   access=mmap.ACCESS_WRITE)
memory1.close()
memory2.close()

memory3 = mmap.mmap(-1,
                   length=8192*2,
                   tagname='blah',
                   access=mmap.ACCESS_WRITE)

