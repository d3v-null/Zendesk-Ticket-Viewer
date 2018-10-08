"""Provide entrypoint for package."""

from .cli.app import ZTVApp
from .core import get_config, setup_logging


def main():
    """Provide a console script entrypoint."""
    config = get_config()

    setup_logging(config)

    # hand over to cli

    ztv_app = ZTVApp(config=config)
    ztv_app.run()


if __name__ == '__main__':
    main()
