"""Provide exceptions to ticket viewer module."""

class ZTVException(Exception):
    """superclass of exceptions raised within this module."""

class ZTVConfigException(ZTVException):
    """Raised when An invalid config has been provided."""
