"""
Provide core functionality to zendesk_ticket_viewer module.

TODO:
    - method to restore pickled tickets into blank api object cache
"""

from __future__ import print_function, unicode_literals

import logging
import pickle
import sys

import requests

import configargparse
from zenpy import Zenpy

from . import PKG_NAME
from .cli_urwid import ZTVApp
from .exceptions import ZTVConfigException

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

    # Logging
    parser.add('--log-file', default='.%s.log' % PKG_NAME)
    parser.add(
        '--verbosity', choices=[
            'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'
        ], default='WARNING'
    )
    parser.add(
        '--pickle-tickets', help=configargparse.SUPPRESS,
        action='store_true'
    )

    config = parser.parse_args(argv)

    return config


def exit_to_console(message):
    """Clean up program and exit, displaying a message."""
    logging.critical(message)
    # TODO: maybe restore terminal settings?
    quit()


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
    zenpy_creds = dict([
        (zenpy_key, getattr(config, config_key)) for zenpy_key, config_key in [
            ('email', 'email'),
            ('password', 'password'),
            ('subdomain', 'subdomain')
        ]
    ])

    zenpy_client = Zenpy(**zenpy_creds)

    return zenpy_client


def pickle_tickets(config, client):
    """Store API tickets for later deserialization."""
    ticket_generator = client.tickets()
    with open('tests/test_data/tickets.pkl', 'wb') as dump_file:
        tickets = [ticket.to_json() for ticket in ticket_generator]
        # needs to be unpickable on PY2 and PY3
        pickle.dump(tickets, dump_file, protocol=2)


def main():
    """Provide Core functionality of ticket viewer."""
    config = get_config()

    setup_logging(config)

    # The Ticket Viewer should handle the API being unavailable
    try:
        validate_connection(config)
    except (
        ZTVConfigException,
        requests.exceptions.ConnectionError,
        requests.exceptions.ProtocolError
    ) as exc:
        exit_to_console("could not validate connection: %s" % exc)
    finally:
        PKG_LOGGER.info("Connection validated")

    # hand over to cli

    zenpy_client = get_client(config)

    if config.pickle_tickets:
        pickle_tickets(config, zenpy_client)

    ztv_app = ZTVApp(zenpy_client)
    ztv_app.run()


if __name__ == '__main__':
    main()
