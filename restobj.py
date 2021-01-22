"""
T-Mobile PCF team generic REST object.

Note(s):
    1. Requires Python 3
    2. For Flask API see: http://flask.pocoo.org/docs/0.11/api
"""
import threading
from datetime import datetime
from sortedcontainers import SortedDict

from flask import Flask, jsonify, request

from logger import LOGGER
from excepts import AlreadyRegistered, NoSuchEndpoint, CannotUnregister

DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

class Endpoint(object):
    """
    Constructor for defining REST endpoint(s).
    """
    def __init__(self, name, description, handler, filters=None):
        """
        Setup the endpoint object internal variables.
        """
        self._name = name
        self._handler = handler
        self._filters = filters
        self._descr = description
        if filters:
            filter_str = "(filter(s): {})".format(', '.join(filters))
            self._descr = "{} {}".format(description, filter_str)
        super().__init__()

    @property
    def name(self):
        """
        Endpoint name (url extension)
        """
        return self._name

    @property
    def description(self):
        """
        Description of the endpoint used for 'help'
        """
        return self._descr

    @property
    def handler(self):
        """
        Function called for handling the endpoint.
        """
        return self._handler


class RESTObject(object):
    """
    This class is meant to be a base (or mixin) class.  It provides
    a general REST interface which allows the subclass to register any
    enpoint and handler that it wishes.
    """
    _commands = {}
    _flaskapp = None

    def __init__(self, port=None, service_name=None, autostart=False,
                 name='endpoints'):
        """
        Register endpoints and start up the flask listening thread.
        """
        self._default_endpoints = [
            #  Basic command enpoints
            Endpoint('state', 'service state', self._cmd_state),
            Endpoint('__empty', 'service state', self._cmd_state),
            Endpoint('showall', 'show registered commands', self._cmd_show_all),
            Endpoint('help', 'show registered commands', self._cmd_show_all),
        ]
        self._default_epoint_names = [ep.name for ep in self._default_endpoints]

        LOGGER.debug("Creating RESTObject")
        self._service_name = service_name
        self._flask_port = port
        self._host_ip = '0.0.0.0'
        self._name = name

        LOGGER.debug("RESTObject registering default endpoints")
        self.register_multiple_endpoints(self._default_endpoints)
        self._start_time = datetime.now().strftime(DATE_FORMAT)

        # See: http://flask.pocoo.org/docs/0.11/api/#url-route-registrations
        self._flaskapp = Flask(__name__)
        LOGGER.debug("RESTObject adding flask rules")
        self._flaskapp.add_url_rule('/', view_func=self._service_request,
                                    defaults={'rest_request': '__empty'})
        self._flaskapp.add_url_rule('/<rest_request>',
                                    view_func=self._service_request)
        if autostart:
            LOGGER.debug("RESTObject create thread object")
            self._flask_thread = threading.Thread(target=self.start,
                                                  args=(),
                                                  kwargs={})
            LOGGER.debug("RESTObject starting background thread and flask app")
            self._flask_thread.start()

    def start(self, *args, **kwargs):
        """
        Run the flask thread.
        """
        hostaddr = kwargs.get('host', self._host_ip)
        portnum = kwargs.get('port', self._flask_port)
        LOGGER.debug("RESTObject starting flask app on %s:%s", hostaddr, str(portnum))
        self._flaskapp.run(host=hostaddr, port=portnum)

    def register_multiple_endpoints(self, endpoints):
        """
        Register several endpoints.
        """
        for epoint in endpoints:
            self.register_endpoint(epoint)

    def register_endpoint(self, endpoint):
        """
        Register a (new) monitoring endpoint.
        """
        if endpoint.name in self._commands.keys():
            raise AlreadyRegistered(endpoint.name)

        LOGGER.debug("RESTObject register endpoint %s", endpoint.name)
        self._commands[endpoint.name] = (endpoint.description, endpoint.handler)

    def unregister_endpoint_by_name(self, endpoint_name):
        """
        Unregister a monitoring endpoint (by name).
        """
        if endpoint_name not in self._commands:
            raise NoSuchEndpoint(endpoint_name)

        if endpoint_name in [ep.name for ep in self._default_endpoints]:
            raise CannotUnregister(endpoint_name)

        LOGGER.debug('RESTObject unregister endpoint "%s"', endpoint_name)
        self._commands.pop(endpoint_name)

    # # #
    # The following commands are used by this base class and are
    # not to be called by inheriting (child) classes.
    def _cmd_state(self, *args):     #  pylint: disable=unused-argument
        """
        Default/builtin command: service state.
        """
        rtn_dict = {'status': 'up',
                    'start_time': self._start_time,
                    'current_time': datetime.now().strftime(DATE_FORMAT)
                   }
        if hasattr(self, 'version'):
            rtn_dict['version'] = self.version
        return jsonify(rtn_dict)

    def _cmd_show_all(self, *args):  #  pylint: disable=unused-argument
        """
        command: show all registered commands.
        """
        showlist = {'default': SortedDict(), self._name: SortedDict()}
        for epoint, val in self._commands.items():
            if not epoint.startswith('__'):
                sublabel = 'default' if \
                           epoint in self._default_epoint_names else self._name
                showlist[sublabel][epoint] = val[0]
        return jsonify(showlist)

    @staticmethod
    def _unknown_request(*args, **kwargs):
        """
        Handle requests to unregistered endpoint(s).
        """
        (epoint, _) = args
        return jsonify('No such endpoint: {}'.format(epoint))

    def _service_request(self, rest_request):
        """
        Generic request handler: intercept all http requests and dispatch
        to the handler registered for that endpoint.
        """

        """
        TODO / PLANNED:
            1. foundrystats.py will go away
            2. cf_agent.py will replace foundrystats
                a. cf_agent will register a single catchall endpoint
                b. the cf_agent catchall will parse org/space/etc
                   from the URL, and __IT__ will dispatch to the handler
        """
        _, epoint_entry = self._commands.get(rest_request,
                                             ('', self._unknown_request))
        return epoint_entry(rest_request, request.args)
