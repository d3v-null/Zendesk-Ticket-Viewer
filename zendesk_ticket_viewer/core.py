import sys

import configargparse
from zenpy import Zenpy


def get_config(argv=None):
    """ Parse arguments from cli, env and config files. """

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

def main():
    """ Provide Core functionality of ticket viewer. """

    config = get_config()

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
