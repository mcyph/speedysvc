from datetime import datetime
from shmrpc.toolkit.html_tools.escape import E


# VERBOSE??
NOTSET = 0
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

_END_COLOUR = '\033[0m'
STDERR = -1
STDOUT = -2


class __LogEntryType:
    date_time_format_console = ('',
                                '')
    service_format_console = ('\033[92m',
                              _END_COLOUR)  # Green
    date_time_format_html = ('',
                             '')
    service_format_html = ('<span style="color: darkgreen">',
                           '</span>')  # Green

    def __init__(self, t, level, pid, port, svc, msg):
        """
        Create a log entry.

        :param t: the time when the log entry occurred
        :param level: a log level, e.g. ERROR, or INFO
        :param pid: the process ID from which the event occurred
        :param port: the port of the service
        :param svc: the name of the service
        :param msg: the log message
        """
        self.t = t
        self.level = level
        self.pid = pid
        self.port = port
        self.svc = svc
        self.msg = msg

    def to_dict(self):
        return {
            't': self.t,
            'level': self.level,
            'pid': self.pid,
            'port': self.port,
            'svc': self.svc,
            'msg': self.msg
        }

    def to_text(self, include_service=True, include_date=True, include_time=True):
        """
        Get plain text (monochrome) formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :return: coloured console-formatted entries,
                 compatible with only Unix terminals
        """
        return self._log_item_formatted(
            ('', ''), ('', ''), ('', ''),
            include_service, include_date, include_time
        )

    def to_coloured_console(self, include_service=True, include_date=True, include_time=True):
        """
        Get coloured console-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :return: coloured console-formatted entries,
                 compatible with only Unix terminals
        """
        return self._log_item_formatted(
            self.format_console,
            self.service_format_console,
            self.date_time_format_console,
            include_service, include_date, include_time
        )

    def to_html(self, include_service=True, include_date=True, include_time=True):
        """
        Get coloured html-formatted log messages.

        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :return: coloured html-formatted entries
        """
        return self._log_item_formatted(
            self.format_html,
            self.service_format_html,
            self.date_time_format_html,
            include_service, include_date, include_time,
            escape_html=True
        )

    def _log_item_formatted(self,
                            colour_template,
                            service_colour_template,
                            date_time_colour_template,
                            include_service=True,
                            include_date=True,
                            include_time=True,
                            escape_html=False):
        """
        Format a log message.

        :param colour_template: a two-tuple of (start formatting, end formatting)
                                for log messages
        :param service_colour_template: a two-tuple of (start formatting, end formatting)
                                        for service name/pid/port
        :param date_time_colour_template: a two-tuple of (start formatting, end formatting)
                                          for dates/times
        :param include_service: whether to include the service's name/port
        :param include_date: whether to include the date of the message
        :param include_time: whether to include the time of the message
        :param escape_html:
        :return: the formatted log message, as a str
        """
        item = ''

        # Add service info
        if include_service:
            item += f"{service_colour_template[0]}[" \
                    f"{self.svc}:" \
                    f"{self.port} " \
                    f"pid {self.pid}" \
                    f"]{service_colour_template[1]} "

        # Add time/date info
        DTimeFormats = {
            # keys -> (include date, include time)
            (True, True): '%Y-%m-%d %H:%M:%S',
            (True, False): '%Y-%m-%d',
            (False, True): '%H:%M:%S'
        }
        if include_date or include_time:
            formatted_time = datetime.utcfromtimestamp(
                self.t
            ).strftime(
                DTimeFormats[include_date, include_time]
            )
            item += f"{date_time_colour_template[0]}" \
                    f"[{formatted_time}]" \
                    f"{date_time_colour_template[1]} "

        # Add log message
        #
        # Open closed principle violation here :P
        # but I can't think of many instances where
        # I'd use anything other than just stdout/stderr
        # right now.
        msg = (
            E(self.msg) if escape_html else self.msg
        )

        if colour_template:
            start, end = colour_template
            item += start + msg + end
        else:
            item += msg

        return item


class NotSetLogEntry(__LogEntryType):
    format_console = ('',
                      '')
    format_html = ('',
                   '')
    description = None
    writes_to = STDOUT


class InfoLogEntry(__LogEntryType):
    format_console = ('',
                      '')
    format_html = ('',
                   '')
    description = 'info'
    writes_to = STDOUT


class DebugLogEntry(__LogEntryType):
    format_console = ('',
                      '')  # FIXME
    format_html = ('<span style="color: gray">',
                   '</span>')
    description = 'dbg'
    writes_to = STDOUT


class WarningLogEntry(__LogEntryType):
    format_console = ('\033[93m',
                      _END_COLOUR)
    format_html = ('<span style="color: orange>',
                   '</span>')
    description = 'warn'
    writes_to = STDERR


class ErrorLogEntry(__LogEntryType):
    format_console = ('\033[91m',
                      _END_COLOUR)
    format_html = ('<span style="color: darkred">',
                   '</span>')
    description = 'err'
    writes_to = STDERR


class CriticalLogEntry(__LogEntryType):
    format_console = ('\033[1m\033[91m',
                      _END_COLOUR+_END_COLOUR)
    format_html = ('<span style="font-weight: bold; color: darkred">',
                   '</span>')
    description = 'critical'
    writes_to = STDERR


def dict_to_log_entry(D) -> __LogEntryType:
    """
    Convert a log dict as saved to log files to a relevant
    __LogEntryType subclass

    :param D: the log dict
    :return: a __LogEntryType subclass (e.g. InfoLogEntry)
    """
    level = D['level']
    if 0 > level > 10:
        return NotSetLogEntry(**D)
    elif 10 > level > 20:
        return DebugLogEntry(**D)
    elif 20 > level > 30:
        return InfoLogEntry(**D)
    elif 30 > level > 40:
        return WarningLogEntry(**D)
    elif 40 > level > 50:
        return ErrorLogEntry(**D)
    elif 50 > level > 60:
        return CriticalLogEntry(**D)
    else:
        raise Exception("Unknown log level: %s" % level)
