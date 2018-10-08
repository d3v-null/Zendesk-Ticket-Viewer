"""Provide exceptions to ticket viewer module."""


class ZTVException(Exception):
    """Superclass exceptions raised within this module."""


class ZTVConfigException(ZTVException):
    """Raised when An invalid config has been provided."""
    remedy = 'Use the `--help` switch to display usage instructions'
