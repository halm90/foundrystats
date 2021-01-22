"""
T-Mobile PCF team Cloud Foundry statistis gathering REST endpoint(s) (aka: agent)

Note(s):
    1. Requires Python 3
"""
import werkzeug
from collections import defaultdict
from flask import jsonify

from cfstats_agent import CFStatsAgent
from logger import LOGGER
from parameters import PARAMS
from restobj import RESTObject, Endpoint

FOUNDRYSTATS_REST_VERSION = '0.1'

class CFStatsREST(RESTObject):
    """
    The REST API: field incoming requests and dispatch to
    the appropriate handler.
    """
    version = FOUNDRYSTATS_REST_VERSION
    def __init__(self, service_name=None, port=None):
        """
        Initialize the REST object.
        """
        self._additional_endpoints = [
            Endpoint('apps', 'get app info (same as get_app)',
                     self._get_app,
                     filters=["appGuid", "spaceGuid", "appName", "showField"]),
            Endpoint('services', 'get service info (same as get_service)',
                     self._get_service,
                     filters=["serviceGuid", "serviceName", "showField"]),
            Endpoint('app_list', 'get the list of all apps',
                     self._app_list),
            Endpoint('get_app', 'get app info for all or specific apps(s)',
                     self._get_app,
                     filters=["appGuid", "spaceGuid", "appName",
                              "showField", "withMetadata"]),
            Endpoint('get_org', 'get org info for all or specific org(s)',
                     self._get_org, filters=["orgGuid", "orgName"]),
            Endpoint('get_service', 'get service info',
                     self._get_service,
                     filters=["serviceGuid", "serviceName", "showField"]),
            Endpoint('org_list', 'get the list of all org guid/names',
                     self._org_list),
            Endpoint('service_list', 'get the list of all service guid/names',
                     self._service_list),
            Endpoint('space_list', 'get of all spaces',
                     self._space_list),
            Endpoint('get_space', 'get space info for all or specific spaces',
                     self._get_space, filters=["spaceGuid", "spaceName"]),
        ]

        LOGGER.debug("Initializing CFStatsRest object")
        super().__init__(port=port, service_name=service_name)
        LOGGER.debug("Register endpoints")
        self.register_multiple_endpoints(self._additional_endpoints)

        #  The fetcher object encapsulates the interface to the Cloud Foundry
        #  DB fetcher.  This is currently a placeholder (see note in agent)
        self._cfagent = CFStatsAgent()

    @staticmethod
    def _keys_to_lower(filters):
        """
        Convert all keys in an ImmutableMultiDict to lower case
        """
        convert_dict = defaultdict(list)
        for k, v in filters.lists():
            convert_dict[k.lower()] += v
        newfilt = werkzeug.datastructures.MultiDict(convert_dict)
        return newfilt

    def _app_list(self, *args):
        """
        Get the list of all apps
        """
        LOGGER.debug("REST requested app list")
        return jsonify(self._cfagent.app_list)

    def _get_app(self, *args):
        """
        Get data for the all apps or the one(s) specified
        """
        LOGGER.debug("REST requested app data")
        (_, filters) = args
        apps = self._cfagent.get_app(filters=self._keys_to_lower(filters))
        return jsonify(apps)

    def _get_org(self, *args):
        """
        Get the data for all orgs or the one(s) specified
        """
        LOGGER.debug("REST requested org data")
        (_, filters) = args
        return jsonify(self._cfagent.get_org(self._keys_to_lower(filters)))

    def _get_service(self, *args):
        """
        Get data for the all services or the one(s) specified
        """
        LOGGER.debug("REST requested service data")
        (_, filters) = args
        svc_params = ['bound_app_count', 'created_at', 'dashboardUrl',
                      'guid' 'lastOperation', 'last_operation_state',
                      'name', 'org_guid', 'org_name', 'service',
                      'service_guid', 'service_plan', 'servicePlanGuid',
                      'service_provider', 'service_version', 'spaceGUID',
                      'space_name', 'updated_at'
                     ]

        svcs = self._cfagent.get_service(fields=svc_params,
                                         filters=self._keys_to_lower(filters))
        return jsonify(svcs)

    def _get_space(self, *args):
        """
        Get the data for all spaces or the one(s) specified
        """
        LOGGER.debug("REST requested space data")
        (_, filters) = args
        return jsonify(self._cfagent.get_space(self._keys_to_lower(filters)))

    def _org_list(self, *args):
        """
        Get the list of all orgs
        """
        LOGGER.debug("REST requested org list")
        return jsonify(self._cfagent.org_list)

    def _service_list(self, *args):
        """
        Get the list of all service guid/names
        """
        LOGGER.debug("REST requested service list")
        return jsonify(self._cfagent.service_list)

    def _space_list(self, *args):
        """
        Get the list of all spaces
        """
        LOGGER.debug("REST requested space list")
        return jsonify(self._cfagent.space_list)


if __name__ == "__main__":
    LOGGER.debug("Main starting")

    # Instantiate and start the REST API
    cfstats = CFStatsREST(service_name=__name__)
    cfstats.start(port=PARAMS['STATS_PORT'])
