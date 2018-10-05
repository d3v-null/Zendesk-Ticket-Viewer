"""Provide core functionality to zendesk_ticket_viewer module."""

from __future__ import print_function, unicode_literals

import sys

import configargparse
import requests
from zenpy import Zenpy

from .exceptions import ZTVConfigException


def get_config(argv=None):
    """Parse arguments from cli, env and config files."""
    argv = sys.argv[1:] if argv is None else argv

    parser = configargparse.ArgumentParser(
        description="View Zendesk support ticket information",
    )

    parser.add('--config-file', '-c', is_config_file=True)
    parser.add('--subdomain', env_var='ZENDESK_SUBDOMAIN')
    parser.add('--email', env_var='ZENDESK_EMAIL')
    parser.add('--password', env_var='ZENDESK_PASSWORD')

    config = parser.parse_args(argv)

    print(parser.format_values())

    return config

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
        raise ZTVConfigException("Subdomain provided does not exist")



def main():
    """Provide Core functionality of ticket viewer."""
    config = get_config()

    # The Ticket Viewer should handle the API being unavailable
    validate_connection()

    zenpy_creds = dict([
        (zenpy_key, getattr(config, config_key)) for zenpy_key, config_key in [
            ('email', 'email'),
            ('password', 'password'),
            ('subdomain', 'subdomain')
        ]
    ])

    zenpy_client = Zenpy(**zenpy_creds)

    ticket_generator = zenpy_client.tickets()

    first_ticket = ticket_generator[25:][0]

    print(first_ticket.to_json())

if __name__ == '__main__':
    main()
