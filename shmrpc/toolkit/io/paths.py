from sys import getfilesystemencoding
from os.path import expanduser
from tempfile import gettempdir
#import warnings


def get_cfg_dir():
    """
    os.path.expanduser doesn't support Unicode, but 
    it returns a byte string so it can be decoded
    """
    try: 
        return expanduser('~').decode(getfilesystemencoding(), 
                                      'ignore')
    except: 
        return expanduser('~')


def gettempdir():
    # TODO: DOES THIS SUPPORT UNICODE???
    #warnings.warn("FIX THE TEMP DIR HACKS!")
    #return r'H:\Temp\Flazzle' # HACK!
    try: 
        return gettempdir().decode(getfilesystemencoding(), 
                                   'ignore')
    except: 
        return gettempdir()
