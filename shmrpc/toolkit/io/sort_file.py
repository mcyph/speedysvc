from heapq import heappop, heappush
from itertools import islice, cycle
from tempfile import gettempdir
import os
from codecs import open


def merge(chunks,key=None):
    if key is None: 
        key = lambda x : x
    
    values = []
    for index, chunk in enumerate(chunks):
        try:
            iterator = iter(chunk)
            value = next(iterator)
        except StopIteration:
            try:
                chunk.close()
                os.remove(chunk.name)
                chunks.remove(chunk)
            except: 
                pass
        else: 
            heappush(values,((key(value),index,value,iterator,chunk)))

    while values:
        k, index, value, iterator, chunk = heappop(values)
        yield value
        
        try: 
            value = next(iterator)
        except StopIteration:
            try:
                chunk.close()
                os.remove(chunk.name)
                chunks.remove(chunk)
            except: 
                pass
        else: 
            heappush(values,(key(value),index,value,iterator,chunk))


def batch_sort(input, output, key=None, buffer_size=32000, tempdirs=[]):
    if not tempdirs: 
        tempdirs.append(gettempdir())
    
    input_file = open(input, 'rb', 'utf-8', 'replace')
    
    try:
        input_iterator = iter(input_file)
        chunks = []
        try:
            for tempdir in cycle(tempdirs):
                current_chunk = list(islice(input_iterator,buffer_size))
                
                if current_chunk:
                    current_chunk.sort(key=key)
                    output_chunk = open(os.path.join(tempdir,'%06i'%len(chunks)), 'w+b', 'utf-8', 'replace')
                    output_chunk.writelines(current_chunk)
                    output_chunk.flush()
                    output_chunk.seek(0)
                    chunks.append(output_chunk)
                else: 
                    break
        except:
            for chunk in chunks:
                try:
                    chunk.close()
                    os.remove(chunk.name)
                except: 
                    pass
            
            if output_chunk not in chunks:
                try:
                    output_chunk.close()
                    os.remove(output_chunk.name)
                except: 
                    pass
            return
    finally: 
        input_file.close()
    
    output_file = open(output, 'wb', 'utf-8', 'replace')
    try: 
        output_file.writelines(merge(chunks,key))
    finally:
        for chunk in chunks:
            try:
                chunk.close()
                os.remove(chunk.name)
            except: 
                pass
        
        output_file.close()


if __name__ == '__main__':
    batch_sort(
        r'C:\Documents and Settings\Administrator\Local Settings\Temp\4-Similar.tmp',
        r'C:\Documents and Settings\Administrator\Local Settings\Temp\4-Similar-Sorted.tmp',
    )
