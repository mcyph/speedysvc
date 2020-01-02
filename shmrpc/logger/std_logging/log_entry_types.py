CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0


class LogEntryType:
    text_weight = 'underline'


class Critical:
    def __init__(self, msg):
        pass

    def to_html(self):
        pass

    def to_coloured_console(self):
        pass


class Error:
    def to_html(self):
        pass


class Warning:
    pass


class Info:
    pass


class Debug:
    pass


class NotSet:
    pass

