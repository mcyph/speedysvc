import json
import time
from shmrpc.logger.std_logging.MemoryCachedLog import MemoryCachedLog
from datetime import datetime
from toolkit.html_tools.escape import E


STDOUT = 0
STDERR = 1
SERVICE_INFO = 2

# Log levels?? =======================================================================
CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0


class ConsoleColors:
    # https://stackoverflow.com/questions/287871/how-to-print-colored-text-in-terminal-in-python
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class HTMLColors:
    HEADER = '<span style="font-weight: bold; color: purple">'
    OKBLUE = '<span style="color: darkblue">'
    OKGREEN = '<span style="color: darkgreen">'
    WARNING = '<span style="color: orange">'
    FAIL = '<span style="color: darkred">'
    ENDC = '</span>'
    BOLD = '<span style="font-weight: bold">'
    UNDERLINE = '<span style="text-decoration: underline">'


class FIFOJSONLog(MemoryCachedLog):
    def __init__(self, path, max_cache=500000):  # 500kb
        """
        A disk-backed, in-memory-cached JSON log, delimited by
        newlines before each entry so as to be able to figure
        out the last readable entry, and remove any partially
        overwritten ones in the cache.

        \n{'t': [time], 'msg': msg, '}

        """
        MemoryCachedLog.__init__(self, path, max_cache=max_cache)

    #====================================================================#
    #                          Add Log Entries                           #
    #====================================================================#

    def write_to_log(self, pid, port, service_name, msg, typ=STDOUT):
        """

        :param msg:
        :return:
        """
        self._write_line(json.dumps({
            'type': typ,
            'pid': pid,
            't': int(time.time()),
            'msg': msg,
            'port': port,
            'svc': service_name
        }))

    #====================================================================#
    #                          Get Log Entries                           #
    #====================================================================#

    def iter_from_disk(self):
        """
        Iterate through all log items from disk -
        not just the ones in-memory, or from this session
        """
        for line in self._iter_from_disk():
            yield json.loads(line)

    def iter_from_cache(self, offset=None):
        """
        Iterate through cache log items - yield the JSON log dicts
        Better to use this in most cases, as is much faster
        """
        for x, line in enumerate(self._iter_from_cache(offset)):
            if not x:
                continue
            yield json.loads(line)

    def get_console_log(self,
                        include_service=True,
                        include_date=True,
                        include_time=True):
        """
        Get coloured console-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :return: coloured console-formatted entries,
                 compatible with only Unix terminals
        """

        return self._format_log_messages(
            ConsoleColors,
            include_service, include_date, include_time
        )

    def get_html_log(self,
                     include_service=True,
                     include_date=True,
                     include_time=True):
        """
        Get coloured html-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :return: coloured html-formatted entries
        """

        return self._format_log_messages(
            HTMLColors,
            include_service, include_date, include_time,
            escape_html=True
        )

    def _format_log_messages(self,
                             FormatColors,
                             include_service=True,
                             include_date=True,
                             include_time=True,
                             escape_html=False):
        """

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :return:
        """
        L = []
        for DLogItem in self.iter_from_cache():
            item = ''

            # Add service info
            if include_service:
                item += f"{FormatColors.HEADER}[" \
                        f"{DLogItem['svc']}:" \
                        f"{DLogItem['port']} " \
                        f"pid {DLogItem['pid']}" \
                        f"]{FormatColors.ENDC} "

            # Add time/date info
            DTimeFormats = {
                # keys -> (include date, include time)
                (True, True): '%Y-%m-%d %H:%M:%S',
                (True, False): '%Y-%m-%d',
                (False, True): '%H:%M:%S'
            }
            if include_date or include_time:
                formatted_time = datetime.utcfromtimestamp(
                    DLogItem['t']
                ).strftime(
                    DTimeFormats[include_date, include_time]
                )
                item += f"{FormatColors.OKGREEN}" \
                        f"[{formatted_time}]" \
                        f"{FormatColors.ENDC} "

            # Add log message
            #
            # Open closed principle violation here :P
            # but I can't think of many instances where
            # I'd use anything other than just stdout/stderr
            # right now.
            msg = (
                E(DLogItem['msg']) if escape_html else DLogItem['msg']
            )
            if DLogItem['type'] == STDOUT:
                item += msg
            elif DLogItem['type'] == STDERR:
                item += f"{FormatColors.FAIL}" \
                        f"{msg}" \
                        f"{FormatColors.ENDC}"
            elif DLogItem['type'] == SERVICE_INFO:
                # This is just meant for "service is starting" etc messages
                item += msg
            else:
                raise Exception(f"Unknown message type: {DLogItem['type']}")

            L.append(item)
        return self.spindle, '\n'.join(L)
