import psutil
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

PLOT_NUM_SECS = 10


def get_dequeue():
    return deque(
        PLOT_NUM_SECS*[0], PLOT_NUM_SECS
    )


def get_proc_by_name(name):
    for proc in psutil.process_iter():
        if proc.name() == name:
            return proc
    raise Exception("No process by name %s" % name)


cpu_fifo = get_dequeue()

disk_read_fifo = get_dequeue()
disk_write_fifo = get_dequeue()

shared_mem_fifo = get_dequeue()
physical_mem_fifo = get_dequeue()
swap_mem_fifo = get_dequeue()

proc = get_proc_by_name('firefox')


while 1:
    plt.title('A tale of 2 subplots')
    plt.xlabel('time (s)')

    # Plot the CPU info
    plt.subplot(3, 1, 1)  # nrows, ncols, index

    cpu_fifo.appendleft(proc.cpu_percent())
    x1 = np.asarray(range(PLOT_NUM_SECS))
    y1 = np.asarray(cpu_fifo)

    plt.plot(x1, y1, '.-')
    plt.ylabel('% CPU / # Processes')

    # Plot the disk info
    disk_read_fifo.appendleft(proc.io_counters().read_bytes)
    disk_write_fifo.appendleft(proc.io_counters().write_bytes)

    x2 = np.asarray(range(PLOT_NUM_SECS))
    y2_1 = np.asarray(disk_read_fifo)
    y2_2 = np.asarray(disk_write_fifo)

    plt.subplot(3, 1, 2)
    plt.plot(x2, y2_1, '.-')
    plt.plot(x2, y2_2, '.-')
    plt.ylabel('Disk read/write in bytes')

    # Plot the memory info
    mem_info = proc.memory_full_info()

    shared_mem_fifo.appendleft(mem_info.shared)
    physical_mem_fifo.appendleft(mem_info.rss)
    swap_mem_fifo.appendleft(mem_info.vms)
    print('shared:', shared_mem_fifo)
    print('physical_mem_fifo:', physical_mem_fifo)
    print('swap_mem_fifo:', swap_mem_fifo)

    x3 = np.asarray(range(PLOT_NUM_SECS))
    y3_1 = np.asarray(shared_mem_fifo)
    y3_2 = np.asarray(physical_mem_fifo)
    y3_3 = np.asarray(swap_mem_fifo)

    plt.subplot(3, 1, 3)
    plt.plot(x3, y3_1, '.-')
    plt.plot(x3, y3_2, '.-')
    plt.plot(x3, y3_3, '.-')
    plt.ylabel('Memory usage in bytes')

    plt.show()
    sleep(1)
