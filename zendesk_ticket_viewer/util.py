"""Utilities for the zendesk_ticket_viewer package."""

import functools

import requests
import zenpy

from .exceptions import ZTVConfigException


def wrap_connection_error(injected, on_fail, on_success=None, attempting=None):
    """
    Inject a connection action into a try/catch statement, failing gracefully.

    Args
    ----
        injected (:obj:`function`): the function to be injected into the
            statement which takes no arguments
        on_fail (:obj:`function`): the function to call on failure which
            accepts a message and an exception as arguments
        on_success (:obj:`function`, optional): the function to call on success
            which takes no arguments
        attempting (:obj:`str`): a string what is being attempted
    """
    response = None
    try:
        response = injected()
    except (
        ZTVConfigException,
        requests.exceptions.ConnectionError,
        zenpy.lib.exception.APIException
    ) as exc:
        on_fail(attempting, exc)
        return
    if on_success:
        on_success()
    return response
