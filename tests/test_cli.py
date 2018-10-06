"""
Tests for CLI module.

TODO:
-----
    Test for crash when resize terminal
"""

from __future__ import generators

import itertools
import json
import os
import unittest
import pickle

import urwid
import zenpy
from context import TEST_DATA_DIR
from six import MovedModule, add_move
from zendesk_ticket_viewer.cli_urwid import (TicketCell, TicketColumn,
                                             TicketList)

if True:
    # Ensure certain libraries can be imported the same way in PY2/3
    add_move(MovedModule('mock', 'mock', 'unittest.mock'))
    from six.moves import mock


class TestCliMocked(unittest.TestCase):

    def test_ticket_cell_render(self):
        """
        Test that ticket cells truncates rendered text by default
        """

        cell = TicketCell("some long text")
        self.assertEqual(
            cell.render((10,))._text,
            [b'some long ']
        )

    def test_ticket_column_render(self):
        """
        Test that ticket columns render correctly.
        """

        column = TicketColumn(
            header=TicketCell("Header A"),
            body=urwid.ListBox(urwid.SimpleListWalker([
                TicketCell("Cell A1"),
                TicketCell("Cell A2 - with some text to truncate"),
                TicketCell("Cell A3"),
            ]))
        )

        composite = column.render((10, 10), True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )

        self.assertEqual(
            text_content,
            [
                b'Header A  ',
                b'Cell A1   ',
                b'Cell A2 - ',
                b'Cell A3   ',
                b'          ',
                b'          ',
                b'          ',
                b'          ',
                b'          ',
                b'          '
            ]
        )

    @mock.patch('zenpy.Zenpy')
    def with_mocked_tickets(self, injected, tickets, zenpy_mock):
        """
        Call a given `injected` so that Zenpy.tickets() returns a mocked value.

        Args:
            injected (:obj:`function`): The function to be injected into the
                mocked context which takes a `zenpy.Zenpy` client as an arg
            tickets (:obj:)
            zenpy_mock : Provided by the mock.patch decorator
        """

        zenpy_mock.return_value = mock.MagicMock(tickets=mock.MagicMock(
            return_value=tickets
        ))
        client = zenpy.Zenpy()
        return injected(client)

    def test_ticket_list_render(self):
        tickets_path = os.path.join(TEST_DATA_DIR, 'tickets.pkl')
        with open(tickets_path, 'rb') as tickets_file:
            # dumb hack to unpickle a file from python3
            tickets = (
                zenpy.lib.api_objects.Ticket(**json.loads(ticket))
                for ticket in pickle.load(tickets_file)
            )

        def injected(client):
            return TicketList(client)

        ticket_list = self.with_mocked_tickets(injected, tickets)

        composite = ticket_list.render((48, 10), True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )
        expected = [
            b'Ticket # ', b'Subject      ', b'Type         ', b'Priority     ',
            b'       1 ', b'Sample ticket', b'Incident     ', b'normal       ',
            b'       2 ', b'velit eiusmod', b'Ticket       ', b'-            ',
            b'       3 ', b'excepteur lab', b'Ticket       ', b'-            ',
            b'       4 ', b'ad sunt qui a', b'Ticket       ', b'-            ',
            b'       5 ', b'aliquip molli', b'Ticket       ', b'-            ',
            b'       6 ', b'nisi aliquip ', b'Ticket       ', b'-            ',
            b'       7 ', b'cillum quis n', b'Ticket       ', b'-            ',
            b'       8 ', b'proident est ', b'Ticket       ', b'-            ',
            b'       9 ', b'veniam ea eu ', b'Ticket       ', b'-            '
        ]
        # import pudb; pudb.set_trace()
        self.assertEqual(text_content, expected)
