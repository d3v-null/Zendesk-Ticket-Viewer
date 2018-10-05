import shlex
import unittest

import configargparse
import requests

from six import MovedModule, add_move
from zendesk_ticket_viewer.core import get_config, validate_connection
from zendesk_ticket_viewer.exceptions import ZTVConfigException

if True:
    # Ensure certain libraries can be imported the same way in PY2/3
    add_move(MovedModule('mock', 'mock', 'unittest.mock'))
    from six.moves import mock


class TestMainMocked(unittest.TestCase):
    def test_get_config_argv(self):
        """ Test that the get_config can parse the argv parameter. """
        dummy_subdomain = 'foo.com'
        dummy_email = 'bar@baz.com'
        dummy_password = 'qux'

        # construct argv from dummy data
        dummy_args = shlex.split(
            (
                "--subdomain '{subdomain}' "
                "--email '{email}' "
                "--password '{password}'"
            ).format(
                subdomain=dummy_subdomain,
                email=dummy_email,
                password=dummy_password
            )
        )
        config = get_config(argv=dummy_args)
        self.assertEqual(config.subdomain, dummy_subdomain)
        self.assertEqual(config.email, dummy_email)
        self.assertEqual(config.password, dummy_password)

    @mock.patch('requests.Session')
    def mock_validate_connection(self, subdomain, mock_status_code, session_mock):
        """
        Call `validate_connection` using a mocked session which always returns a given status_code.

        Args:
            subdomain (str): The subdomain which is being tested
            mock_status_code (int): the status code which is always returned by
                the mocked session
        """
        mock_response = requests.Response()
        mock_response.status_code = mock_status_code
        session_mock.return_value = mock.MagicMock(get=mock.MagicMock(
            return_value=mock_response
        ))
        session = requests.Session()
        config = configargparse.Namespace()
        config.subdomain = subdomain
        validate_connection(config, session)


    def test_validate_connection_good_subdomain(self):
        # No exceptions should be thrown
        self.mock_validate_connection('good_subdomain', 200)

    def test_validate_connection_no_subdomain(self):
        with self.assertRaises(ZTVConfigException):
            self.mock_validate_connection(None, None)

    def test_validate_connection_bad_subdomain(self):
        with self.assertRaises(ZTVConfigException):
            self.mock_validate_connection('bad_subdomain', 301)
