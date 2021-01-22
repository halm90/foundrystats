"""
T-Mobile PCF team CloudFoundry 'cf-stats' agent database table schemas.

Note(s):
"""

class CFApps(object):
    """
    Structure defining applications table
    """
    name = 'applications'
    columns = ["buildpack",
               "command",
               "detectedBuildpack",
               "detectedStartCommand",
               "diskQuota",
               "dockerImage",
               "guid",
               "healthCheckTimeout",
               "healthCheckType",
               "healthCheckHTTPEndpoint",
               "instances",
               "memory",
               "name",
               "packageState",
               "packageUpdatedAt",
               "spaceGUID",
               "stackGUID",
               "stagingFailedDescription",
               "stagingFailedReason",
               "state"
              ]


class CFServiceBindings(object):
    """
    Structure defining service bindings table.
    Used to 'bind' application to service instance.
    """
    name = 'service_bindings'
    columns = ["guid",
               "appGUID",
               "serviceInstanceGUID"
              ]


class CFServices(object):
    """
    Structure defining services table
    """
    name = 'service_instances'
    columns = ["dashboardURL",
               "guid",  # guid of the service instance
               "lastOperation"
               "name",
               "serviceDescription",
               "serviceGUID",   # guid of the service (type)
               "serviceLabel",
               "servicePlanGUID",
               "servicePlanName",
               "spaceGUID",
               "tags",
               "type",
              ]


class CFSpaces(object):
    """
    Structure defining spaces table
    """
    name = 'spaces'
    columns = ["guid",
               "organizationGUID",
               "name",
               "allowSSH",
               "spaceQuotaDefinitionGUID"
              ]


class CFOrganizations(object):
    """
    Structure defining organizations table
    """
    name = 'organizations'
    columns = ["guid",
               "name",
               "quotaDefinitionGUID",
               "defaultIsolationSegmentGUID"
              ]


class CFRouteMapping(object):
    """
    Structure defining route mapping table
    """
    name = 'route_mappings'
    columns = ["guid",
               "appGUID",
               "routeGUID"
              ]


class CFDomains(object):
    """
    Structure defining domains table
    """
    name = 'domains'
    columns = ["guid",
               "name",
               "routerGroupGUID",
               "routerGroupType",
               "type"
              ]


class CFRoutes(object):
    """
    Structure defining routes table
    """
    name = 'routes'
    columns = ["guid",
               "host",
               "path",
               "port",
               "domainGUID",
               "spaceGUID"
              ]
