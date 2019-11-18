import io
import psutil
import numpy as np
from time import sleep
from collections import deque
import matplotlib.pyplot as plt


PLOT_NUM_SECS = 50
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

    #===========================================================#
    #                      Miscellaneous                        #
    #===========================================================#

    def get_dequeue(self):
        return deque(
            PLOT_NUM_SECS*[0], PLOT_NUM_SECS
        )

    def get_proc_by_name(self, name):
        for proc in psutil.process_iter():
            if proc.name() == name:
                return proc
        raise Exception("No process by name %s" % name)

    def __deque_as_np(self, a):
        return np.asarray(list(reversed(a)))

    #===========================================================#
    #                        Poll Data                          #
    #===========================================================#

    def poll_data(self):
        """
        A function to allow polling separate to showing the plot,
        e.g. from a separate thread, and allowing getting the
        plot itself separately via AJAX or other methods
        """
        self.__add_to_cpu_info()
        self.__add_to_disk_info()
        self.__add_to_mem_info()

    #===========================================================#
    #                       Output Plot                         #
    #===========================================================#

    def show_plot(self):
        figure = self.__get_figure()
        plt.show()

    def output_plot_to_buffer(self, path):
        figure = self.__get_figure()
        plt.figure()
        plt.plot([1, 2])
        plt.title("test")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        return buf

    def output_plot_to_file(self, path):
        figure = self.__get_figure()
        plt.savefig(path)

    def __get_figure(self):
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
            nrows=2, ncols=2
        )
        fig.set_size_inches(10, 2)
        fig.set_dpi(85)  # 850px width??

        self.__plot_cpu_info(ax1)
        self.__plot_disk_info(ax2)
        self.__plot_mem_info(ax4)

        return fig

    #===========================================================#
    #                         CPU Info                          #
    #===========================================================#

    def __add_to_cpu_info(self):
        self.cpu_fifo.appendleft(
            self.proc.cpu_percent()
        )

    def __plot_cpu_info(self, ax):
        """
        Plot the CPU info
        """
        x1 = np.asarray(range(PLOT_NUM_SECS))
        y1 = self.__deque_as_np(self.cpu_fifo)

        plot1, = ax.plot(x1, y1, '.-')
        axes = plt.gca()
        axes.set_ylim([0.0, 100.0])
        ax.legend(
            [plot1],
            ["cpu %"], # For # processes?
            loc='upper left'
        )
        ax.grid()
        plt.ylabel('CPU usage')

    #===========================================================#
    #                        Disk Info                          #
    #===========================================================#

    def __add_to_disk_info(self):
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

    def __plot_disk_info(self, ax):
        """
        Plot the disk info
        """
        x2 = np.asarray(range(PLOT_NUM_SECS))
        y2_1 = self.__deque_as_np(self.disk_read_fifo)
        y2_2 = self.__deque_as_np(self.disk_write_fifo)

        plot1, = ax.plot(x2, y2_1, '.-')
        plot2, = ax.plot(x2, y2_2, '.-')
        ax.legend(
            [plot1, plot2],
            ["disk reads", "disk writes"],
            loc='upper left'
        )
        ax.grid()
        plt.ylabel('Disk usage')

    #===========================================================#
    #                       Memory Info                         #
    #===========================================================#

    def __add_to_mem_info(self):
        mem_info = self.proc.memory_full_info()
        self.shared_mem_fifo.appendleft(mem_info.shared / ONE_MEGABYTE)
        self.physical_mem_fifo.appendleft(mem_info.rss / ONE_MEGABYTE)
        self.swap_mem_fifo.appendleft(mem_info.vms / ONE_MEGABYTE)  # ???

    def __plot_mem_info(self, ax):
        """
        Plot the memory info
        """
        x3 = np.asarray(range(PLOT_NUM_SECS))
        y3_1 = self.__deque_as_np(self.shared_mem_fifo)
        y3_2 = self.__deque_as_np(self.physical_mem_fifo)
        y3_3 = self.__deque_as_np(self.swap_mem_fifo)

        plot1, = ax.plot(x3, y3_1, '.-')
        plot2, = ax.plot(x3, y3_2, '.-')
        plot3, = ax.plot(x3, y3_3, '.-')
        ax.legend(
            [plot1, plot2, plot3],
            ["shared", "physical", "swap"],
            loc='upper left'
        )
        ax.grid()
        plt.ylabel('Memory usage')


plot_process_info = PlotProcessInfo()

while 1:
    for x in range(10):
        plot_process_info.poll_data()
        plot_process_info.show_plot()
        sleep(0.5)
