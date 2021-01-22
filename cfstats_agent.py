"""
T-Mobile PCF team CloudFoundry 'cf-stats' agent.

Note(s):
    1. Requires Python 3
    2. The CFStatsAgent is the 'agent' interface between the REST object
       (foundrystats.py) and the fetcher database. It isolates the REST api
       (foundrystats, restobj) from the database, and allows the REST module(s)
       to be unaware of either the fetcher or the DB/caching mechanism.

    3. TODO: the agent methods do not (yet) communicate with the fetcher,
       but rather depend on the fetcher to keep the DB updated.
"""
import json

from bb_fetcher import BBFetcher
from logger import LOGGER
from parameters import PARAMS
from statsdb import StatsDB
from tables import (CFApps, CFServices, CFSpaces,
                    CFOrganizations, CFRouteMapping)


class CFStatsAgent(object):
    """
       Object interfacing the REST API and the fetcher database.  The actual
       DB queries are executed in StatsDB, and that's where the supporting
       functions reside.  That module has no real knowledge of table structure.
       That knowledge resides here, and so the queries are formed here.
    """
    def __init__(self):
        """
        Initialize the API object

        TODO: The intent is to use REST messaging to communicate with the
              fetcher in the event that data is not in the DB to request
              missing records and/or update the DB.

        :params fetcher: the fetcher to contact for DB update
        """
        self._foundation = PARAMS['FOUNDATION']
        # Acquire the database connection(s)
        self._cf_db = StatsDB()
        self._bb_fetch = BBFetcher()

        super().__init__()

    @staticmethod
    def _missing_fields(requested, available):
        """
        Given 2 lists (a list of requested table columns and a list of
        available table columns), return a 2-tuple: list of requested
        items not in 'available' and a list of requested items that are
        in 'available' (set intersection).

        :param requested: list of requested columns
        :param available: list of columns in the table
        :return: (list requested not available, list requested and available)
        """
        reqset = set(requested)
        if requested and requested != '*':
            present = sorted(reqset & set(available))
            missing = sorted(reqset ^ set(present))
        else:
            present = available
            missing = []
        return (missing, present)

    @staticmethod
    def _get_filter_list(filters, key, to_lower=False):
        """
        Given a MultiDict type filter object and a key get the list
        corresponding to that key and turn all of the list entries
        into quoted strings (suitable for SQL query).  If requested
        make the values lower case.  If a key is present in the MultiDict
        but the value is empty then the empty quoted string is NOT returned.

        :param filters: the MultiDict
        :param key: the key whose list value is to be returned
        :param to_lower: flag indicating values are to be changed to lower case
        :return: list of quoted string values
        """
        lst = list(filter(None, filters.getlist(key)))
        rtn = ['"{}"'.format(val) for val in lst]
        if to_lower:
            rtn = [itm.lower() for itm in rtn]
        return rtn

    @property
    def app_list(self):
        """
        Get the list of known apps.
        """
        LOGGER.debug("Retrieve (short) app list")
        applist = self._cf_db.select(CFApps, ['guid', 'name'])
        return applist

    @property
    def service_list(self):
        """
        Get the list of known services.

        TODO: add service query (list all services of certain type)
        """
        LOGGER.debug("Retrieve (short) service list")
        svclist = self._cf_db.select(CFServices, ['guid', 'name'])
        return svclist

    @property
    def org_list(self):
        """
        Get the list of known orgs.
        """
        LOGGER.debug("Retrieve (short) org list")
        orglist = self._cf_db.select(CFOrganizations, ['guid', 'name'])
        return orglist

    @property
    def space_list(self):
        """
        Get the list of known spaces.

        TODO: convert to DB
        """
        LOGGER.debug("Retrieve (short) space list")
        spclist = self._cf_db.select(CFSpaces, ['guid', 'name'])
        return spclist

    def get_org(self, filters=None):
        """
        Get the org data for all orgs or just the one(s) specified if
        filters are given.

        :param filters: ImmutableMultiDict with optional request filter(s)
        """
        table = CFOrganizations
        columns = table.columns
        org_sql = 'SELECT {} '.format(','.join(columns)) \
                  + '   FROM {}'.format(table.name)

        orgs = None
        if filters:
            # fetch the filters, turn them into lists of quoted strings
            org_guids = self._get_filter_list(filters, 'orgguid')
            org_names = self._get_filter_list(filters, 'orgname', True)

            if sum(map(bool, [org_guids, org_names])) > 1:
                orgs = "Specify only orgGuid or orgName"
                LOGGER.error(orgs)
            else:
                if org_guids:
                    org_sql += ' WHERE guid in ({})'.format(','.join(org_guids))
                if org_names:
                    org_sql += ' WHERE name in ({})'.format(','.join(org_names))

        if not orgs:
            cur = self._cf_db.query(org_sql)
            orgs = [self._cf_db.row_to_dict(row, columns) for row in cur]
        return orgs

    def get_app(self, filters=None):
        """
        Get the app data for all apps or just the one(s) specified if
        filters are given.

        :param filters: ImmutableMultiDict with optional request filter(s)
        """
        # Use a list of tuples to assure ordering of labels and results
        # The tuple pairs are "display name" and "source_table.column_name"
        fields = [('buildpack', 'ap.buildpack'),
                  ('disk_quota', 'ap.diskQuota'),
                  ('docker_image', 'ap.dockerImage'),
                  ('guid', 'ap.guid'),
                  ('health_check_timeout', 'ap.healthCheckTimeout'),
                  ('health_check_type', 'ap.healthCheckType'),
                  ('instances', 'ap.instances'),
                  ('memory', 'ap.memory'),
                  ('name', 'ap.name'),
                  ('org_guid', 'og.guid'),
                  ('org_name', 'og.name'),
                  ('package_updated_at', 'ap.packageUpdatedAt'),
                  ('space_guid', 'sp.guid'),
                  ('space_name', 'sp.name'),
                  ('stack_guid', 'ap.stackGUID'),
                  ('state', 'ap.state'),
                  ('service_names', 'GROUP_CONCAT(DISTINCT si.name SEPARATOR ", ")'),
                  ('urls', 'GROUP_CONCAT(DISTINCT ' + \
                           'CONCAT(rt.host, ".", dm.name) SEPARATOR ", ")'),
                 ]

        non_query_fields = ('director', 'foundation')
        app_params, col_names = zip(*fields)
        app_sql = 'SELECT {} '.format(','.join(col_names))
        app_sql += ('    FROM applications AS ap'
                    '    LEFT JOIN service_bindings AS sb ON sb.appGUID=ap.guid'
                    '    LEFT JOIN service_instances AS si ON si.guid=sb.serviceInstanceGUID'
                    '    LEFT JOIN spaces AS sp ON ap.spaceGUID=sp.guid'
                    '    LEFT JOIN organizations AS og ON sp.organizationGUID=og.guid'
                    '    LEFT JOIN route_mappings AS rm ON rm.appGUID=ap.guid'
                    '    LEFT JOIN routes AS rt ON rt.guid = rm.routeGUID'
                    '    LEFT JOIN domains AS dm ON dm.guid=rt.domainGUID')

        apps = None
        discard_fields = None
        incl_meta = False
        if filters:
            # fetch the filters, turn them into lists of quoted strings
            app_guids = self._get_filter_list(filters, 'appguid')
            app_spaces = self._get_filter_list(filters, 'spaceguid')
            app_names = self._get_filter_list(filters, 'appname', True)
            meta_flag = filters.get('withmetadata', 'False').lower()
            incl_meta = True if meta_flag in ['true', 'yes'] else incl_meta

            if sum(map(bool, [app_guids, app_spaces, app_names])) > 1:
                apps = "Specify only appGuid, spaceGuid or appName"
                LOGGER.error(apps)
            else:
                if app_guids:
                    app_sql += ' WHERE ap.guid in ({})'.format(','.join(app_guids))
                if app_spaces:
                    app_sql += ' WHERE si.spaceGUID in ({})'.format(','.join(app_spaces))
                if app_names:
                    app_sql += ' WHERE ap.name in ({})'.format(','.join(app_names))

            requested_fields = set(filters.getlist('showfield'))
            if requested_fields:
                all_fields = app_params + non_query_fields
                requested_available = set(all_fields).intersection(requested_fields)
                if requested_available != requested_fields:
                    LOGGER.info("Requested fields not available: %s",
                                requested_fields - requested_available)
                discard_fields = set(all_fields) - requested_available

        app_sql += ' GROUP BY ap.guid'
        if not apps:
            cur = self._cf_db.query(app_sql)
            # Create a list of all rows, with each row converted to a dictionary.
            # Add foundation key/value to each list entry.
            # apps = [dict(self._cf_db.row_to_dict(row, app_params),
            #             **{'foundation': PARAMS['FOUNDATION']}) for row in cur]
            apps = []
            new_row = True
            for row in cur:
                rowdict = self._cf_db.row_to_dict(row, app_params)
                rowdict['foundation'] = self._foundation
                director = None
                org = rowdict.get('org_name')
                if org:
                    director = \
                        self._bb_fetch.director_by_org_name(org,
                                                            refresh_on_miss=new_row)
                    new_row = False
                rowdict['director'] = director or 'Unknown'
                if discard_fields:
                    for f in discard_fields:
                        rowdict.pop(f, None)
                if incl_meta:
                    rowdict['metadata'] = \
                        self._bb_fetch.get_metadata_by_org_name(org,
                                                                refresh_on_miss=new_row)
                    new_row = False

                apps.append(rowdict)
        return apps

    def get_space(self, filters=None):
        """
        Get the space data for all spaces or just the one(s) specified if
        filters are given.

        :param filters: ImmutableMultiDict with optional request filter(s)
        """
        table = CFSpaces
        columns = table.columns
        spc_sql = 'SELECT {} '.format(','.join(columns)) \
                  + '   FROM {}'.format(table.name)

        spaces = None
        if filters:
            # fetch the filters, turn them into lists of quoted strings
            spc_guids = self._get_filter_list(filters, 'spaceguid')
            spc_names = self._get_filter_list(filters, 'spacename', True)

            if sum(map(bool, [spc_guids, spc_names])) > 1:
                spaces = "Specify only spaceGuid or spaceName"
                LOGGER.error(spaces)
            else:
                if spc_guids:
                    spc_sql += ' WHERE guid in ({})'.format(','.join(spc_guids))
                if spc_names:
                    spc_sql += ' WHERE name in ({})'.format(','.join(spc_names))

        if not spaces:
            cur = self._cf_db.query(spc_sql)
            spaces = []
            for row in cur:
                rowdict = self._cf_db.row_to_dict(row, columns)
                rowdict['foundation'] = self._foundation
                spaces.append(rowdict)
        return spaces

    def get_service(self, fields=None, filters=None):
        """
        Get the service data for all services or just the one(s) specified if
        filters are given.

        :param filters: ImmutableMultiDict with optional request filter(s)

        """
        # Use a list of tuples to assure ordering of labels and results
        # The tuple pairs are "display name" and "source_table.column_name"
        fields = [
            ('bound_app_count', 'COUNT(DISTINCT sb.appGUID)'),
            ('dashboard_url', 'si.dashboardURL'),
            ('guid', 'si.guid'),
            ('LAST_OPERATION', 'si.lastOperation'),
            ('name', 'si.name'),
            ('org_guid', 'org.guid'),
            ('org_name', 'org.name'),
            ('service', 'si.type'),
            ('service_plan_guid', 'si.servicePlanGUID'),
            ('service_guid', 'si.serviceGUID'),
            ('service_plan', 'si.servicePlanName'),
            ('space_guid', 'si.spaceGUID'),
            ('space_name', 'sp.name'),
        ]
        lastop_map = {'type': 'last_operation',
                      'state': 'last_operation_state',
                      'created_at': 'created_at',
                      'updated_at': 'updated_at'
                     }

        svc_params, col_names = zip(*fields)
        non_query_fields = ('director', 'foundation')
        svc_sql = 'SELECT {} '.format(','.join(col_names))
        svc_sql += ('FROM service_instances as si'
                    ' LEFT JOIN spaces AS sp ON sp.guid=si.spaceGUID'
                    ' LEFT JOIN organizations AS org ON org.guid=sp.organizationGUID'
                    ' LEFT JOIN service_bindings AS sb ON sb.serviceInstanceGUID=si.guid ')
        services = None
        discard_fields = None
        if filters:
            # fetch the filters, turn them into lists of quoted strings
            svc_guids = self._get_filter_list(filters, 'serviceguid')
            svc_names = self._get_filter_list(filters, 'servicename', True)

            if sum(map(bool, [svc_guids, svc_names])) > 1:
                services = ["Specify only serviceGuid or serviceName"]
                LOGGER.error(services)
            else:
                if svc_guids:
                    svc_sql += 'AND si.guid in ({}) '.format(','.join(svc_guids))
                if svc_names:
                    svc_sql += 'AND si.name in ({}) '.format(','.join(svc_names))

            requested_fields = set(filters.getlist('showfield'))
            if requested_fields:
                all_fields = non_query_fields + tuple(lastop_map.values()) + \
                             tuple(p for p in svc_params if p != 'LAST_OPERATION')
                requested_available = set(all_fields).intersection(requested_fields)
                if requested_available != requested_fields:
                    LOGGER.info("Requested fields not available: %s",
                                requested_fields - requested_available)
                discard_fields = set(all_fields) - requested_available
        svc_sql += ('GROUP BY si.guid')
        if not services:
            cur = self._cf_db.query(svc_sql)
            services = []
            new_row = True
            # Create a list of all rows, with each row converted to a dictionary.
            # Add foundation key/value to each list entry, and unpack 'last
            # operation' fields.
            for row in cur:
                rowdict = self._cf_db.row_to_dict(row, svc_params)
                rowdict['foundation'] = self._foundation
                if rowdict.get('org_name'):
                    rowdict['director'] = \
                        self._bb_fetch.director_by_org_name(rowdict['org_name'],
                                                            refresh_on_miss=new_row)
                    new_row = False
                for k, v in json.loads(rowdict.pop('LAST_OPERATION')).items():
                    try:
                        rowdict[lastop_map[k]] = v
                    except KeyError:
                        # Ignore fields in result that we don't care to map
                        pass
                if discard_fields:
                    for f in discard_fields:
                        rowdict.pop(f, None)
                services.append(rowdict)
        return services
