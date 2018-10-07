import shlex
import unittest
import os

import requests

import configargparse
from context import TEST_DATA_DIR
from six import MovedModule, add_move
from zendesk_ticket_viewer.core import (get_client, get_config,
                                        validate_connection)
from zendesk_ticket_viewer.exceptions import ZTVConfigException

if True:
    # Ensure certain libraries can be imported the same way in PY2/3
    add_move(MovedModule('mock', 'mock', 'unittest.mock'))
    from six.moves import mock

class TestBase(unittest.TestCase):
    """
    Base test case containing useful
    """
    dummy_subdomain = 'foo.com'
    dummy_email = 'bar@baz.com'
    dummy_password = 'qux'
    config = configargparse.Namespace(
        subdomain=dummy_subdomain,
        email=dummy_email,
        password=dummy_password,
        unpickle_tickets=True,
        pickle_path=os.path.join(TEST_DATA_DIR, 'tickets.pkl')
    )

class TestMainMocked(TestBase):

    def test_get_config_argv(self):
        """Test that the get_config can parse the argv parameter."""

        # construct argv from dummy data
        dummy_args = shlex.split(
            (
                "--subdomain '{subdomain}' "
                "--email '{email}' "
                "--password '{password}'"
            ).format(
                subdomain=self.dummy_subdomain,
                email=self.dummy_email,
                password=self.dummy_password
            )
        )
        config = get_config(argv=dummy_args)
        self.assertEqual(config.subdomain, self.dummy_subdomain)
        self.assertEqual(config.email, self.dummy_email)
        self.assertEqual(config.password, self.dummy_password)

    @mock.patch('requests.Session')
    def mock_validate_connection(self, subdomain, status_code, session_mock):
        """
        Validate cinnection using a session with a mocked status_code.

        Args:
            subdomain (str): The subdomain which is being tested
            status_code (int): the status code which is always returned by
                the mocked session
            session_mock : Provided by the mock.patch decorator
        """
        mock_response = requests.Response()
        mock_response.status_code = status_code
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

    def test_get_client_mocked(self):
        config = configargparse.Namespace(
            subdomain=self.dummy_subdomain,
            email=self.dummy_email,
            password=self.dummy_password
        )
        api = get_client(config)
        self.assertEqual(api.tickets.subdomain, config.subdomain)
        self.assertEqual(api.tickets.session.auth, (config.email, config.password))
