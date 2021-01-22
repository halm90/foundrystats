"""
foundrystats logger functions.
"""
import logging
import sys

from parameters import PARAMS

APPNAME = 'foundrystats'


def get_logger(appname=None, level=None):
    """
    Get a logger object for application-wide use.
    """
    avail_levels = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO,
                    'WARNING': logging.WARNING, 'ERROR': logging.ERROR,
                    'CRITICAL': logging.CRITICAL}

    appname = appname or PARAMS.get('APPNAME', APPNAME)
    loglevel = str(level or PARAMS['LOG_LEVEL']).upper()

    logger = logging.getLogger(appname)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    if loglevel in avail_levels:
        print("Setting log level to {}".format(loglevel))
        logger.setLevel(avail_levels[loglevel])
    else:
        print("Can't set log level to {}".format(loglevel))
    return logger


LOGGER = get_logger()
