"""
Provide core functionality to zendesk_ticket_viewer module.

TODO:
    - method to restore pickled tickets into blank api object cache
"""

from __future__ import print_function, unicode_literals

import functools
import json
import logging
import pickle
import sys

import requests

import configargparse
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


def exit_to_console(message=None, exc=None):
    """Clean up program and exit, displaying a message."""
    message = "Failure in %s" % message if message else "Fatal Error"
    logging.critical(message)
    if exc:
        logging.critical(exc)

    padding = 1
    lines = []
    for _ in range(2):
        lines.insert(0, "*" * (2 * padding + len(message) + 2))
    for _ in range(padding * 2):
        lines.insert(1, "*%s*" % (" " * (2 * padding + len(message))))
    lines.insert(padding + 1, "*" + " " * padding + message + " " * padding + "*")
    print( '\n'.join(lines) )
    # TODO: if exc is type excption, do stack trace
    # TODO: maybe restore terminal settings?
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
        exit_to_console("invalid log level string: %s\n%s" % (
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
        )
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

    zenpy_client = Zenpy(**zenpy_args)

    if getattr(config, 'unpickle_tickets', None):
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


def main():
    """Provide Core functionality of ticket viewer."""
    config = get_config()

    setup_logging(config)

    # The Ticket Viewer should handle the API being unavailable
    wrap_connection_error(
        functools.partial(validate_connection, config),
        attempting="Validate connection",
        on_fail=functools.partial(
            exit_to_console
        ),
        on_success=functools.partial(
            PKG_LOGGER.info, "Connection validated"
        )
    )

    # hand over to cli

    zenpy_client = get_client(config)

    if config.pickle_tickets:
        pickle_tickets(config, zenpy_client)

    ztv_app = ZTVApp(zenpy_client)
    ztv_app.run()


if __name__ == '__main__':
    main()
