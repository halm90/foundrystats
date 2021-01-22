"""
T-Mobile PCF team CloudFoundry 'cf-stats' agent BitBucket fetcher interface.

The Bitbucket org-mgmt application periodically queries Bitbucket for org
data and updates its own cache.  That application provides a REST API which
we query here and make available to this application as dictionaries.

Note(s):
    1. Requires Python 3
"""
from collections import defaultdict
from urllib3.exceptions import HTTPError
import requests

from logger import LOGGER
from parameters import PARAMS


class InvalidFoundation(Exception):
    """
    A mapping from foundation name to Bitbucket fetcher contexts can't
    be found for the given foundation.
    """

class ContextNotAvailable(Exception):
    """
    Requested context is not available from Bitbucket fetcher
    """

class BBFetcher(list):
    """
    This object provides an interface between the Bitbucket org-mgmt
    application REST interface and the cf-stats agent/presenter.  The
    org-mgmt REST API is presented as a dictionary to the agent.
    """
    _context_map = {"npe": "PCF_NPE",
                    "prd": "PCF_PRD",
                    "cde": "PCF_CDE",
                   }
    _unmapped_contexts = ["stg"]

    def __init__(self, context=None):
        """
        Initialize the Bitbucket org management interface object.
        """
        self._org_url = PARAMS['BB_ORG_FETCHER_URL']
        self._cached_metadata = defaultdict(dict)
        self._remote_cache_timestamp = None
        self._bb_request_time_limit = int(PARAMS["BB_REQUEST_TIME_LIMIT"])

        try:
            context_key = PARAMS['FOUNDATION'].split('-')[1][:3]
            self._context = context or self._context_map[context_key]
        except KeyError:
            if context_key not in self._unmapped_contexts:
                LOGGER.error("Can't map foundation %s", context_key)
                raise InvalidFoundation
            else:
                self._context = None

        if self._context:
            available_contexts = self._context_list()
            if not available_contexts \
               or self._context not in available_contexts:
                LOGGER.error("Context %s (foundation %s) not in context list %s",
                             self._context,
                             PARAMS['FOUNDATION'],
                             ','.join(available_contexts) if available_contexts
                                                          else "(no contexts)")
                raise ContextNotAvailable

        LOGGER.info("Initialize fetcher (context(s): %s)", self._context)
        super().__init__()

    def _request(self, url, json=True):
        """
        Send get request to the given url and handle errors.
        Return json if indicated else raw data.

        :param url: the target url to send the get request to
        :param json: true if json result required or raw data if false
        :return: request response (json or raw)
        """
        LOGGER.debug("Fetcher GET request: %s", url)
        retn = None
        try:
            rsp = requests.get(url, timeout=self._bb_request_time_limit)
        except HTTPError as err:
            LOGGER.error("HTTP request error (url %s): %s", url, err)
        except Exception as exn:
            LOGGER.error("Unknown error requesting from %s: %s", url, exn)
        else:
            if rsp.status_code == requests.codes.ok:
                retn = rsp.json() if json else rsp.data
            else:
                LOGGER.info("Error requesting from BB fetcher: %s", url)
                LOGGER.debug("Query error %d (%s): %s",
                             rsp.status_code, rsp.reason, rsp.text)
        return retn

    def _context_list(self):
        """
        Get a list of contexts from the BB fetcher.
        """
        url = "{}/contexts/".format(self._org_url)
        contexts = self._request(url)
        if not contexts:
            LOGGER.warning("No contexts available")
        return contexts

    def _get_fetcher_cache_timestamp(self):
        """
        Retrieve the Bitbucket fetcher cache timestamp.
        """
        status_data = self._get_fetcher_status()
        return status_data.get('cache_timestamp') if status_data else None

    def _get_fetcher_status(self):
        """
        Retrieve the Bitbucket fetcher (cache) status.
        """
        url = "{}/reader_status".format(self._org_url)
        LOGGER.debug("Requesting BB fetcher reader status (%s)", url)
        return self._request(url)

    def _refresh_cached_metadata(self, org=None):
        """
        (Re)fill the local cache of metadata from the BB fetcher (if
        the local cache is stale).
        """
        if not self._context:
            LOGGER.info("No valid Bitbucket fetcher context")
            return {}

        remote_timestamp = self._get_fetcher_cache_timestamp()
        if not remote_timestamp or remote_timestamp == self._remote_cache_timestamp:
            LOGGER.info("Remote cache not ready (or timestamps match), skip refresh")
            return
        self._remote_cache_timestamp = remote_timestamp

        url = "{}/contexts/{}/orgs_metadata".format(self._org_url, self._context)
        if org:
            url += "/{}".format(org)

        LOGGER.debug("Requesting BB fetcher bulk download")
        metadata = self._request(url)
        if metadata:
            self._cached_metadata.update({org: metadata[org]
                                          for org in metadata
                                          if metadata[org]})
            LOGGER.debug("Cached %d org entries for context %s",
                         len(metadata), self._context)

        LOGGER.debug("Cached %d orgs for context %s",
                     len(self._cached_metadata), self._context)

    def get_metadata_by_org_name(self, org, refresh_on_miss=True):
        """
        Get all of the metadata for a given org.

        If the cache is empty or the given org is not in cache then refresh
        the whole cache.  The cache refresh will only refresh if the cache
        timestamp has changed since the last refresh.
        """
        org = org.lower()
        if (org not in self._cached_metadata) and refresh_on_miss:
            LOGGER.debug("Org not in cache, refresh")
            self._refresh_cached_metadata()
        else:
            LOGGER.debug("Org/director retrieved from cache")
        return self._cached_metadata.get(org, {})

    def director_by_org_name(self, org, refresh_on_miss=True):
        """
        Look up the director name(s) given the org name.  Note that org names
        are converted to lower-case.

        If the cache is empty or the given org is not in cache then refresh
        the cache (if refresh_on_miss is set).  The refresh function will
        only refresh the cache if it is stale.

        :param name:
        :return: director name(s)
        """
        org = org.lower()
        LOGGER.debug("Lookup director for org %s", org)
        meta = self.get_metadata_by_org_name(org,
                                             refresh_on_miss=refresh_on_miss)
        director = meta.get('director', 'Unknown')
        LOGGER.debug("Org/director %s/%s", org, director)
        return director
