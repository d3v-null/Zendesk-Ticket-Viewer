import unittest
import shlex

from zendesk_ticket_viewer.core import get_config

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
