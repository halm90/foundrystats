"""
foundrystats application-wide parameters
"""
import os

DEFAULT_LOG_LEVEL = 'DEBUG'
DEFAULT_TOOL_PORT = 8080
DEFAULT_BB_REQUEST_TIME_LIMIT = 10


class SysParams(object):
    """
    A utility class intended to hold all system-wide and configurable
    parameters.  This could be a singleton but need not explicitly be one.
    """
    __params = {}
    _required_env = ['FOUNDATION',
                     'BB_ORG_FETCHER_URL',
                    ]

    _overridable = {
        'LOG_LEVEL': DEFAULT_LOG_LEVEL,
        'STATS_PORT': DEFAULT_TOOL_PORT,
        'CF_URL': None,
        'BB_REQUEST_TIME_LIMIT': DEFAULT_BB_REQUEST_TIME_LIMIT,
    }

    def __init__(self):
        #  Get required environment variables, fail if any are missing.
        missing = []
        for key in self._required_env:
            try:
                self.__params[key] = os.environ[key]
            except KeyError:
                missing.append(key)
        if missing:
            print("ERROR: missing environment variable(s): {}".format(missing))
            exit(1)

        #  Get optional/overridable environment variables
        self.__params.update({key: os.getenv(key, val) for
                              key, val in self._overridable.items()})

    @property
    def params(self):
        """
        Make the (internal) params object a read-only property
        """
        return self.__params


PARAMS = SysParams().params
