import json
import time
from _thread import allocate_lock

from shmrpc.logger.std_logging.MemoryCachedLog import MemoryCachedLog
from shmrpc.logger.std_logging.log_entry_types import dict_to_log_entry, INFO


class FIFOJSONLog(MemoryCachedLog):
    def __init__(self, path, max_cache=5000):  # 5kb
        """
        A disk-backed, in-memory-cached JSON log, delimited by
        newlines before each entry so as to be able to figure
        out the last readable entry, and remove any partially
        overwritten ones in the cache.

        \n{'t': [time], 'msg': msg, '}

        """
        self.lock = allocate_lock()
        MemoryCachedLog.__init__(self, path, max_cache=max_cache)

    #====================================================================#
    #                          Add Log Entries                           #
    #====================================================================#

    def write_to_log(self, t, pid, port, svc, msg, level=INFO):
        """
        Write a message to the log.

        :param t: the unix timestamp from the epoch as returned by time.time()
        :param pid: the process ID from which the event occurred
        :param port: the port of the service
        :param svc: the name of the service
        :param msg: the log message
        :param level: a log level, e.g. ERROR, or INFO
        """
        with self.lock:
            self._write_line(json.dumps({
                't': int(t),
                'level': level,
                'pid': pid,
                'port': port,
                'svc': svc,
                'msg': msg
            }).encode('utf-8'))

    #====================================================================#
    #                          Get Log Entries                           #
    #====================================================================#

    def iter_from_disk(self):
        """
        Iterate through all log items from disk -
        not just the ones in-memory, or from this session
        """
        for line in self._iter_from_disk():
            yield json.loads(line.decode('utf-8'))

    def iter_from_cache(self, offset=None):
        """
        Iterate through cache log items - yield the JSON log dicts
        Better to use this in most cases, as is much faster
        """
        for x, line in enumerate(self._iter_from_cache(offset)):
            yield json.loads(line.decode('utf-8'))

    def get_text_log(self, include_service=True, include_date=True, include_time=True,
                     offset=None):
        """
        Get coloured console-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :param offset: the offset for getting log entries only after this "spindle"
                       point, to prevent having to download the whole lot every time
        :return: a tuple of (current offset, coloured console-formatted entries,
                 compatible with only Unix terminals)
        """
        with self.lock:
            L = []
            for D in self.iter_from_cache(offset):
                log_entry = dict_to_log_entry(D)
                L.append(log_entry.to_text(
                    include_service, include_date, include_time
                ))
            return self.get_fifo_spindle(), L

    def get_coloured_console_log(self, include_service=True, include_date=True, include_time=True,
                                 offset=None):
        """
        Get coloured console-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :param offset: the offset for getting log entries only after this "spindle"
                       point, to prevent having to download the whole lot every time
        :return: a tuple of (current offset, coloured console-formatted entries,
                 compatible with only Unix terminals)
        """
        with self.lock:
            L = []
            for D in self.iter_from_cache(offset):
                log_entry = dict_to_log_entry(D)
                L.append(log_entry.to_coloured_console(
                    include_service, include_date, include_time
                ))
            return self.get_fifo_spindle(), L

    def get_html_log(self, include_service=True, include_date=True, include_time=True,
                     offset=None):
        """
        Get coloured html-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :param offset: the offset for getting log entries only after this "spindle"
                       point, to prevent having to download the whole lot every time
        :return: a tuple of (current offset, coloured html-formatted entries)
        """
        with self.lock:
            L = []
            for D in self.iter_from_cache(offset):
                log_entry = dict_to_log_entry(D)
                L.append(log_entry.to_html(
                    include_service, include_date, include_time
                ))
            return self.get_fifo_spindle(), L


if __name__ == '__main__':
    log = FIFOJSONLog('/tmp/test_fifo_json_log.json')
    log.write_to_log(5454, 555, 55, 'mine', 'message')
    print(log.get_coloured_console_log())
    print(log.get_html_log())
    print(log.get_text_log())
    print(log.get_coloured_console_log())
    print(log.get_html_log())
    print(log.get_text_log())

