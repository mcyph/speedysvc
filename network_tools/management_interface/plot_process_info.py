import psutil
from time import sleep
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

PLOT_NUM_SECS = 10
PLOT_NUM_SUBPLOTS = 3
ONE_MEGABYTE = 1048576


class PlotProcessInfo:
    def __init__(self):
        self.cpu_fifo = self.get_dequeue()

        self.disk_read_fifo = self.get_dequeue()
        self.disk_write_fifo = self.get_dequeue()

        self.shared_mem_fifo = self.get_dequeue()
        self.physical_mem_fifo = self.get_dequeue()
        self.swap_mem_fifo = self.get_dequeue()

        self.proc = self.get_proc_by_name('firefox')

    def get_dequeue(self):
        return deque(
            PLOT_NUM_SECS*[0], PLOT_NUM_SECS
        )

    def get_proc_by_name(self, name):
        for proc in psutil.process_iter():
            if proc.name() == name:
                return proc
        raise Exception("No process by name %s" % name)

    def do_plot(self):
        plt.title('A tale of 2 subplots')
        plt.xlabel('time (s)')

        self.__plot_cpu_info()
        self.__plot_disk_info()
        self.__plot_mem_info()

        plt.show()

    def __plot_cpu_info(self):
        """
        Plot the CPU info
        """
        self.cpu_fifo.appendleft(
            self.proc.cpu_percent()
        )
        x1 = np.asarray(range(PLOT_NUM_SECS))
        y1 = self.__deque_as_np(self.cpu_fifo)

        plt.subplot(PLOT_NUM_SUBPLOTS, 1, 1)  # nrows, ncols, index
        plt.plot(x1, y1, '.-')
        axes = plt.gca()
        #axes.set_xlim([xmin, xmax])
        axes.set_ylim([0.0, 100.0])
        plt.grid()
        plt.ylabel('% CPU / # Processes')

    def __plot_disk_info(self):
        """
        Plot the disk info
        """
        self.disk_read_fifo.appendleft(
            (
                self.proc.io_counters().read_bytes /
                ONE_MEGABYTE
            ) - self.disk_read_fifo[0]
        )
        self.disk_write_fifo.appendleft(
            (
                self.proc.io_counters().write_bytes /
                ONE_MEGABYTE
            ) - self.disk_write_fifo[0]
        )

        x2 = np.asarray(range(PLOT_NUM_SECS))
        y2_1 = self.__deque_as_np(self.disk_read_fifo)
        y2_2 = self.__deque_as_np(self.disk_write_fifo)

        plt.subplot(PLOT_NUM_SUBPLOTS, 1, 2)
        plt.plot(x2, y2_1, '.-')
        plt.plot(x2, y2_2, '.-')
        plt.grid()
        plt.ylabel('Disk read/write MB')

    def __plot_mem_info(self):
        """
        Plot the memory info
        """
        mem_info = self.proc.memory_full_info()

        self.shared_mem_fifo.appendleft(
            mem_info.shared / ONE_MEGABYTE
        )
        self.physical_mem_fifo.appendleft(
            mem_info.rss / ONE_MEGABYTE
        )
        self.swap_mem_fifo.appendleft(
            mem_info.vms / ONE_MEGABYTE
        )
        print('shared:', self.shared_mem_fifo)
        print('physical_mem_fifo:', self.physical_mem_fifo)
        print('swap_mem_fifo:', self.swap_mem_fifo)

        x3 = np.asarray(range(PLOT_NUM_SECS))
        y3_1 = self.__deque_as_np(self.shared_mem_fifo)
        y3_2 = self.__deque_as_np(self.physical_mem_fifo)
        y3_3 = self.__deque_as_np(self.swap_mem_fifo)

        plt.subplot(PLOT_NUM_SUBPLOTS, 1, 3)
        plt.plot(x3, y3_1, '.-')
        plt.plot(x3, y3_2, '.-')
        plt.plot(x3, y3_3, '.-')
        plt.grid()
        plt.ylabel('Memory MB')

    def __deque_as_np(self, a):
        return np.asarray(list(reversed(a)))


plot_process_info = PlotProcessInfo()

while 1:
    plot_process_info.do_plot()
    sleep(1)
