"""
Provide core functionality to zendesk_ticket_viewer module.

TODO:
    - method to restore pickled tickets into blank api object cache
"""

from __future__ import division, print_function, unicode_literals

import functools
import itertools
import json
import logging
import pickle
import sys
import time

import requests

import configargparse
import six
import urwid
import zenpy
from zenpy import Zenpy

from . import PKG_NAME
from .cli_urwid import ZTVApp
from .exceptions import ZTVConfigException
from .util import wrap_connection_error

PKG_LOGGER = logging.getLogger(PKG_NAME)


def get_config(argv=None):
    """Parse arguments from cli, env and config files."""
    argv = sys.argv[1:] if argv is None else argv

    parser = configargparse.ArgumentParser(
        description="View Zendesk support ticket information",
    )

    parser.add('--config-file', '-c', is_config_file=True)

    # Zendesk creds
    parser.add('--subdomain', env_var='ZENDESK_SUBDOMAIN')
    parser.add('--email', env_var='ZENDESK_EMAIL')
    parser.add('--password', env_var='ZENDESK_PASSWORD')

    # Debug / Logging
    parser.add('--log-file', default='.%s.log' % PKG_NAME)
    parser.add(
        '--verbosity', choices=[
            'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'
        ], default='WARNING'
    )
    group = parser.add_mutually_exclusive_group()
    group.add(
        '--pickle-tickets', help=configargparse.SUPPRESS,
        action='store_true'
    )
    group.add(
        '--unpickle-tickets', help=(
            "Load a previously saved pickle file for testing without creds "
            "or internet"
        ),
        action='store_true'
    )
    parser.add(
        '--pickle-path', help="Path to pickle file", metavar="PATH",
        default='tests/test_data/tickets.pkl'
    )

    config = parser.parse_args(argv)

    return config


def critical_error_exit(message=None, exc=None):
    """
    Clean up program and exit, displaying and logging a message.

    Present the message to the user in full screen and is display until an
    input is received.
    """

    # log as critical first in case urwid doesn't work
    message = "Failure in %s" % message if message else "Fatal Error"
    logging.critical(message)
    if exc:
        logging.critical("{} {}".format(exc.__class__, exc))

    widget_list = [
        urwid.Divider()
    ]
    if exc:
        widget_list.extend([
            urwid.Text(str(exc), align='center'),
            urwid.Divider(),
        ])
        if getattr(exc, 'remedy', None):
            widget_list.extend([
                urwid.Text(str(exc.remedy), align='center'),
                urwid.Divider(),
            ])
    widget_list.extend([
        urwid.Text("press any key to exit", align='center'),
        urwid.Divider(),
    ])

    screen = urwid.raw_display.Screen()
    maxcol, maxrow = screen.get_cols_rows()

    box = urwid.Overlay(
        urwid.LineBox(
            urwid.ListBox(urwid.SimpleFocusListWalker(widget_list)),
            title=message,
        ),
        urwid.SolidFill('/'),
        align='center', width=maxcol//2,
        valign='middle', height=maxrow//2
    )

    def stop_nowish(*args):
        time.sleep(1)
        raise urwid.ExitMainLoop()

    loop = urwid.MainLoop(
        widget=box,
        screen=screen,
        unhandled_input=stop_nowish
    )

    loop.run()

    exit()


def setup_logging(config):
    """
    Configure the logging module.

    File-based logging since the console is used for the TUI.

    Args
    ----
        config (:obj:`configargparse.Namespace`): the config namespace which
            must contain `verbosity` (str) and `log_file` (str) attributes
    """
    try:
        PKG_LOGGER.setLevel(getattr(logging, config.verbosity))
    except Exception as exc:
        critical_error_exit("invalid log level string: %s\n%s" % (
            config.verbosity,
            exc
        ))
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    )
    PKG_LOGGER.addHandler(file_handler)


def validate_connection(config, session=None):
    """
    Test a connection to the api base that is credential independent.

    Example of response when subdomain exists:

    ```
    $ curl https://obscura.zendesk.com/access/unauthenticated -v
    < HTTP/1.1 200 OK
    ```

    Example of response when subdomain doesn't exist:
    ```
    $ curl https://nonexistent-subdomain.zendesk.com/access/unauthenticated -v
    < HTTP/1.1 301 Moved Permanently
    ```

    Args
    ----
        config (:obj:`configargparse.Namespace`): the config namespace which
            must contain a `subdomain` attribute
        session (:obj:`requests.Session`, optional): The session object through
            which connections are made (makes mocking easier).

    Raises
    ------
        ZTVConfigException: If an invalid subdomain has been provided.
        requests.exceptions.ConnectionError: If a connection could not be made
            to the subdomain

    """
    if getattr(config, 'unpickle_tickets', None):
        return

    if not config.subdomain:
        raise ZTVConfigException("No subdomain provided")

    if session is None:
        session = requests.Session()

    response = session.get(
        'https://{subdomain}.zendesk.com/access/unauthenticated'.format(
            subdomain=config.subdomain
        ),
        allow_redirects=False
    )
    if response.status_code != 200:
        raise ZTVConfigException(
            "Subdomain provided does not exist: %s" % config.subdomain)


def get_client(config):
    """Given a `config`, create a Zenpy API client."""

    zenpy_args = dict([
        (zenpy_key, getattr(config, config_key, None))
        for zenpy_key, config_key in [
            ('email', 'email'),
            ('password', 'password'),
            ('subdomain', 'subdomain')
        ]
    ])

    unpickle_tickets = getattr(config, 'unpickle_tickets', None)

    try:
        zenpy_client = Zenpy(**zenpy_args)
    except zenpy.lib.exception.ZenpyException as exc:
        if unpickle_tickets:
            zenpy_args['password'] = zenpy_args['password'] or 'dummy_pass'
            zenpy_args['subdomain'] = zenpy_args['subdomain'] \
                or 'dummy_subdomain'
            zenpy_args['email'] = zenpy_args['email'] or 'dummy_email'
            zenpy_client = Zenpy(**zenpy_args)
        else:
            raise ZTVConfigException(str(exc))

    if unpickle_tickets:
        # Chose LRUCache because TTL cache deletes things
        cache = zenpy.ZenpyCache('LRUCache', maxsize=10000)
        # TODO: fill zenpy_client.tickets.cache with data from file
        with open(config.pickle_path, 'rb') as pickle_file:
            for ticket_json in pickle.load(pickle_file):
                ticket_dict = json.loads(ticket_json)
                ticket = zenpy.lib.api_objects.Ticket(**ticket_dict)
                cache[ticket.id] = ticket
        zenpy_client.tickets.cache.mapping['ticket'] = cache

    return zenpy_client


def pickle_tickets(config, client):
    """Store API tickets for later deserialization."""
    ticket_generator = client.tickets()
    with open(config.pickle_path, 'wb') as dump_file:
        tickets = [ticket.to_json() for ticket in ticket_generator]
        # needs to be unpickable on PY2 and PY3
        pickle.dump(tickets, dump_file, protocol=2)
