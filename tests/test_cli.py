"""
Tests for CLI module.
"""

from __future__ import generators

import itertools
import json
import os
import pickle
import unittest
from copy import copy

import urwid
import zenpy
from context import TEST_DATA_DIR
from six import MovedModule, add_move
from zendesk_ticket_viewer.cli_urwid import (AppFrame, BlankPage, TicketCell,
                                             TicketColumn, TicketListPage)

if True:
    # Ensure certain libraries can be imported the same way in PY2/3
    add_move(MovedModule('mock', 'mock', 'unittest.mock'))
    from six.moves import mock


class FakeApp(object):
    """A fake app containing a reference to a client for testing."""
    def __init__(self, client):
        self.client = client

class TestCliMocked(unittest.TestCase):
    expected_start_content = [
    	b' ', b'Ticket # ', b'Subject             ', b'Type      ', b'Priority  ',
    	b'>', b'       1 ', b'Sample ticket: Meet ', b'Incident  ', b'normal    ',
    	b' ', b'       2 ', b'velit eiusmod repreh', b'Ticket    ', b'-         ',
    	b' ', b'       3 ', b'excepteur laborum ex', b'Ticket    ', b'-         ',
    	b' ', b'       4 ', b'ad sunt qui aute ull', b'Ticket    ', b'-         ',
    	b' ', b'       5 ', b'aliquip mollit quis ', b'Ticket    ', b'-         ',
    	b' ', b'       6 ', b'nisi aliquip ipsum n', b'Ticket    ', b'-         ',
    	b' ', b'       7 ', b'cillum quis nostrud ', b'Ticket    ', b'-         ',
    	b' ', b'       8 ', b'proident est nisi no', b'Ticket    ', b'-         ',
    	b' ', b'       9 ', b'veniam ea eu minim a', b'Ticket    ', b'-         '
    ]

    expected_end_content = [
    	b' ', b'Ticket # ', b'Subject             ', b'Type      ', b'Priority  ',
    	b'>', b'     101 ', b'in nostrud occaecat ', b'Ticket    ', b'-         ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          ',
    	b' ', b'         ', b'                    ', b'          ', b'          '
    ]

    def setUp(self):
        tickets_path = os.path.join(TEST_DATA_DIR, 'tickets.pkl')
        with open(tickets_path, 'rb') as tickets_file:
            # dumb hack to unpickle a file from python3
            self.tickets = (
                zenpy.lib.api_objects.Ticket(**json.loads(ticket))
                for ticket in pickle.load(tickets_file)
            )

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

    def test_blank_page(self):
        """
        Test that a blank app page satisfies the AppPage interface.
        """
        def injected(client):
            return BlankPage(FakeApp(client))

        page = self.with_mocked_tickets(injected, self.tickets)
        self.assertEqual(page.page_title, "")
        self.assertTrue(page.page_usage.startswith(""))
        self.assertEqual(page.page_status, "")

    def test_ticket_list(self):
        """
        Test that a ticket list app page satisfies the AppPage interface.
        """
        def injected(client):
            return TicketListPage(FakeApp(client))

        page = self.with_mocked_tickets(injected, self.tickets)
        self.assertEqual(page.page_title, "Ticket List")
        self.assertTrue(page.page_usage.startswith("UP / DOWN"))
        # TODO: finish and test this
        self.assertEqual(page.page_status, "")

    def test_ticket_list_render(self):
        def injected(client):
            return TicketListPage(FakeApp(client))

        ticket_list = self.with_mocked_tickets(injected, self.tickets)

        screen_size = (50, 10)

        composite = ticket_list.render(screen_size, True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )
        self.assertEqual(text_content, self.expected_start_content)

    def test_ticket_list_render_paging_small(self):
        """
        Capture the case where previously, bounds were not checked correctly for
        highlighted_index.
        """
        def injected(client):
            return TicketListPage(FakeApp(client))

        screen_size = (50, 10)

        ticket_list = self.with_mocked_tickets(injected, self.tickets)
        ticket_list.render(screen_size, True)
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page up')
        ticket_list.keypress(screen_size, 'page up')
        ticket_list.keypress(screen_size, 'down')

        composite = ticket_list.render(screen_size, True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )

        expected = copy(self.expected_start_content)
        expected[5] = b' '
        expected[10] = b'>'
        self.assertEqual(text_content, expected)

    def test_ticket_list_render_paging_hard(self):
        """
        Capture the edge case where the last page has less visible tickets
        than the previous page, causing selected_index to fall off visible tickets.
        """
        def injected(client):
            return TicketListPage(FakeApp(client))

        screen_size = (50, 38)

        ticket_list = self.with_mocked_tickets(injected, self.tickets)
        ticket_list.render(screen_size, True)
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')

    def test_ticket_list_render_paging_resize(self):
        """
        Capture the edge case where a widget is resized after scrolling to the
        bottom.
        """
        def injected(client):
            return TicketListPage(FakeApp(client))

        screen_size = (50, 38)

        ticket_list = self.with_mocked_tickets(injected, self.tickets)
        ticket_list.render(screen_size, True)
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')

        screen_size = (50, 10)

        composite = ticket_list.render(screen_size, True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )
        self.assertEqual(text_content, self.expected_end_content)

    def test_appframe_blank(self):
        def injected(client):
            return AppFrame("Test App", client)

        frame = self.with_mocked_tickets(injected, self.tickets)

        screen_size = (50, 10)
        composite = frame.render(screen_size, True)

        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )

        self.assertEqual(text_content, [
        	b'Test App         ', b'                 ', b'                ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  ',
        	b'                                                  '
        ])
