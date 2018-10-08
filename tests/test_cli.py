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

import configargparse
import urwid
import zenpy
from six import MovedModule, add_move
from test_core import TestBase
from zendesk_ticket_viewer.cli.app import AppFrame, ZTVApp
from zendesk_ticket_viewer.cli.pages import (BlankPage, ErrorPage, TicketCell,
                                             TicketListPage, TicketViewPage)
from zendesk_ticket_viewer.cli.widgets import (FormFieldHorizontalPass,
                                               TicketColumn)
from zendesk_ticket_viewer.core import get_client

if True:
    # Ensure certain libraries can be imported the same way in PY2/3
    add_move(MovedModule('mock', 'mock', 'unittest.mock'))
    from six.moves import mock

class TestCliWidgets(TestBase):
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

    def test_form_field_horizontal_pass(self):
        """
        Edge case when `password` is `None`
        """
        wg_pass = FormFieldHorizontalPass(
            "Password: ",
            None,
            key='password'
        )
        canvas = wg_pass.render((30,))
        text_content = [
            text for _, _, text in itertools.chain(*canvas.content())
        ]
        self.assertEqual(
            text_content,
            [b'Password: ', b' ', b'                   ']
        )


class TestCliPages(TestBase):
    # Cache client because it is costly to unpickle every test.
    _client_cache = None

    list_content_start = [
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

    list_content_end = [
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

    view_content_init = [
    	b'        Ticket #', b' ', b'                                 ',
     	b'         Subject', b' ', b'                                 ',
    	b'        Assignee', b' ', b'                                 ',
    	b'            Tags', b' ', b'                                 ',
    	b'            Type', b' ', b'Ticket                           ',
    	b'        Priority', b' ', b'-                                ',
    	b'     Description', b' ', b'                                 ',
    	b'                                                  ',
    	b'                                                  ',
    	b'                                                  '
    ]

    @classmethod
    def setUpClass(cls):
        cls.client = get_client(cls.config)

    def test_blank_page(self):
        """
        Test that a blank app page satisfies the AppPage interface.
        """
        page = BlankPage(AppFrame(client=self.client))
        self.assertEqual(page.page_title, "")
        self.assertTrue(page.page_usage.startswith(""))
        self.assertEqual(page.page_status, "")

    def test_ticket_list(self):
        """
        Test that a ticket list app page satisfies the AppPage interface.
        """

        page = TicketListPage(AppFrame(client=self.client))
        self.assertEqual(page.page_title, "Ticket List")
        self.assertTrue(page.page_usage.startswith("UP / DOWN"))
        # TODO: finish and test this
        self.assertEqual(page.page_status, "")

    def test_ticket_list_render_initial(self):

        ticket_list = TicketListPage(AppFrame(client=self.client))

        screen_size = (50, 10)

        composite = ticket_list.render(screen_size, True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )
        self.assertEqual(text_content, self.list_content_start)

    def test_ticket_list_render_paging_small(self):
        """
        Capture the case where previously, bounds were not checked correctly for
        highlighted_index.
        """

        screen_size = (50, 10)

        ticket_list = TicketListPage(AppFrame(client=self.client))
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

        expected = copy(self.list_content_start)
        expected[5] = b' '
        expected[10] = b'>'
        self.assertEqual(text_content, expected)

    def test_ticket_list_render_paging_hard(self):
        """
        Capture the edge case where the last page has less visible tickets
        than the previous page, causing selected_index to fall off visible tickets.
        """

        screen_size = (50, 38)

        ticket_list = TicketListPage(AppFrame(client=self.client))
        ticket_list.render(screen_size, True)
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')

    def test_ticket_list_render_paging_resize(self):
        """
        Capture the edge case where a widget is resized after scrolling to the
        bottom.
        """

        screen_size = (50, 38)

        ticket_list = TicketListPage(AppFrame(client=self.client))
        ticket_list.render(screen_size, True)
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')
        ticket_list.keypress(screen_size, 'page down')

        screen_size = (50, 10)

        composite = ticket_list.render(screen_size, True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )
        self.assertEqual(text_content, self.list_content_end)

    def test_ticket_view_render_blank(self):

        ticket_view = TicketViewPage(AppFrame(client=self.client))

        screen_size = (50, 10)

        composite = ticket_view.render(screen_size, True)
        text_content = list(
            text for _, _, text in itertools.chain(*composite.content())
        )
        self.assertEqual(text_content, self.view_content_init)

class TestCliApp(TestBase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_client(cls.config)

    def test_appframe_blank(self):
        frame = AppFrame(client=self.client, title="Test App")

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

    def test_appframe_error(self):
        frame = AppFrame(client=self.client, title="Test App")

        frame.add_page('ERROR', ErrorPage)
        frame.modal_fatal_error("message", "exc")

        self.assertEqual(frame.current_page_id, "ERROR")
        self.assertEqual(frame.pages['ERROR'].page_title, "Error: message")
        self.assertEqual(
            frame.pages['ERROR'].error_details,
            "exc\n\npress ctrl-c to exit"
        )

    def test_app_blank(self):
        app = ZTVApp(config=self.config)
        # since unpickle tickets is True, should bypass login
        self.assertEqual(app.frame.current_page_id, 'TICKET_LIST')
        # enter on any list item should show a ticket view
        app.frame.keypress((50, 10), 'enter')
        self.assertEqual(app.frame.current_page_id, 'TICKET_VIEW')
