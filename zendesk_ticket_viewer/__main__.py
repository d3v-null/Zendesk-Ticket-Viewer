"""
Provide main entrypoint for package.
"""
import functools

from .core import (PKG_LOGGER, critical_error_exit, get_client, get_config,
                   pickle_tickets, setup_logging, validate_connection)
from .util import wrap_connection_error
from .cli_urwid import ZTVApp


def main():
    """Provide a console script entrypoint."""
    config = get_config()

    setup_logging(config)

    # The Ticket Viewer should handle the API being unavailable
    wrap_connection_error(
        functools.partial(validate_connection, config),
        attempting="Validate connection",
        on_fail=critical_error_exit,
        on_success=functools.partial(
            PKG_LOGGER.info, "Connection validated"
        )
    )

    zenpy_client = wrap_connection_error(
        functools.partial(get_client, config),
        attempting="Create client",
        on_fail=critical_error_exit,
        on_success=functools.partial(
            PKG_LOGGER.info, "Client created"
        )
    )

    # hand over to cli

    if config.pickle_tickets:
        pickle_tickets(config, zenpy_client)

    ztv_app = ZTVApp(zenpy_client)
    ztv_app.run()


if __name__ == '__main__':
    main()
