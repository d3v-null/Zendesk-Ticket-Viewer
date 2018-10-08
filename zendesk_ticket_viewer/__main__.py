"""
Provide main entrypoint for package.
"""
import functools

from .core import (PKG_LOGGER, critical_error_exit, get_client, get_config,
                   setup_logging, validate_connection)
from .util import wrap_connection_error
from .cli_urwid import ZTVApp


def main():
    """Provide a console script entrypoint."""
    config = get_config()

    setup_logging(config)

    # hand over to cli

    ztv_app = ZTVApp(config=config)
    ztv_app.run()


if __name__ == '__main__':
    main()
