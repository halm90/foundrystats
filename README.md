# FoundryStats
Rewrite of 'cf-stats'.  Present REST endpoints which provide data from the Cloud Foundry controller.

## Getting started
- To set the Concourse pipeline: 
```
cd ci/deploy
fly -t tmo login --concourse-url https://ci.cf.t-mobile.com --team-name px-npe01 -k
fly -t tmo sp -c pipeline.yml -p foundrystats-install-pipeline -l ../vars/common-pipeline-vars.tmpl -l ../vars/npe01-pipeline-vars.tmpl
```

## Required Environment Variables
- `FOUNDATION` => the foundation this app will target. (ie. px-sandbox.example.com)
- `BB_ORG_FETCHER_URL` => URL to query for the Bitbucket fetcher 'org-mgmt' metadata (director/org mapping)
### Optional Environment Variables
- `LOG_LEVEL` => One of DEBUG, WARNING, INFO, CRITICAL, ERROR.  Typically set to INFO, use DEBUG for lots of logging
- `VERIFY` => Set to `False` if ssl validation needs to be skipped
### Operational / overridable Environment Variables (defaults shown in '()')
- `STATS_PORT` => port number that endpoint will bind to

## REST endpoints
This list may not be complete.  This framework is designed to be easily extended, and so endpoints may have been added, removed or renamed.  The `state` and `showall` endpoints should always remain.  In particular `showall` (aka: `help`) will display all currently recognized endponits.
- `/`: a welcome message with the current time, indicating that the service is running.
- `help`: show registered commands
- `showall`: alias for `help`
- `state`: state of this application
-
- `app_list`: get the list of all apps
- `get_app`: get app info for all or specific org(s)
- `get_org`: get org info for all or specific org(s)
- `get_service`: get service info
- `org_list`: get the list of all org guid/names
- `service_list`: get the list of all service guid/names
- `space_list`: get of all spaces
- `get_space`: get space info for all or specific spaces

### Notes:
Some endpoints listed above support HTTP queries:
- `get_app`: _appGuid_, _spaceGuid_, _appName_, _showField_
- `get_org`: _orgGuid_, _orgName_
- `get_service`: _serviceGuid_, _serviceName_, _showField_
- `get_space`: _spaceGuid_, _spaceName_

* *get_app* and *get_service* support _showField_.  Only those fields explicitly named will be retrieved.
* Query strings are case insensitive
* Queries may be strung together, for example:
```
http://..../get_app?appName=some_name&showField=guid&showField=name&showField=memory
```

## Files
- `cfstats_agent.py`: _agent_, interface between REST endpoint and database
- `excepts.py`: application-wide exception definitions
- `foundrystats.py`: REST endpoint, main entry
- `logger.py`: logging facility
- `parameters.py`: environment parameter facility
- `restobj.py`: generic REST object
- `tables.py`: schema definitions for database tables
- `statsdb.py`: generic database object
- `bb_fetcher.py`: query the Bitbucket org management data fetcher REST endpoint
