"""
Provide Command Line Interface for the package using the urwid library.
"""

from __future__ import unicode_literals

from collections import OrderedDict

import configargparse
import urwid
from urwid.compat import with_metaclass

from ..core import PKG_LOGGER
from .pages import (AppElementMixin, BlankPage, TicketListPage, TicketViewPage,
                    WelcomePage)

# TODO: remove numpy dependency, it takes forever to install on WSL'


class AppFrame(urwid.Frame, AppElementMixin):
    """Provide a Frame widget to house a multi-page app."""

    column_meta = OrderedDict([
        ('id', {
            'title': 'Ticket #',
            'sizing': ['fixed', 9],
            'align': 'right',
            'formatter': (lambda x: "{} ".format(x))
        }),
        ('subject', {
            'sizing': ['weight', 2],
        }),
        ('assignee_id', {
            'title': 'Assignee',
            'list_view': False,
        }),
        ('tags', {
            'list_view': False,
            'formatter': (lambda x: ', '.join(x))
        }),
        ('type', {
            'formatter': (lambda x: (x or 'ticket').title())
        }),
        ('priority', {
            'formatter': (lambda x: x or '-')
        }),
        # TODO: conversations
    ])

    key_actions = {
        'esc': 'back',
        # 'e': 'error',
    }

    def __init__(self, client=None, *args, **kwargs):
        """Wrap super __init__ with extra meta."""
        self.title = kwargs.pop('title', '')
        # Mapping of pageIDs to widgets
        self.pages = {
            'BLANK': BlankPage(self)
        }
        # LIFO queue of page IDs that functions as a "history".
        self.page_stack = []
        # API Client,
        self.client = client
        # App event loop
        self.loop = kwargs.pop('loop', None)
        self.__super.__init__(
            header=self.initial_header_widget(),
            body=self.current_page,
            footer=self.initial_footer_widget(),
            *args, **kwargs
        )

    @property
    def config(self):
        """Provide convenient shortcut for app config namespace."""
        return self.loop.config

    @property
    def current_page_id(self):
        """Return the current page id of the app."""
        return self.page_stack[-1] if self.page_stack else "BLANK"

    @property
    def current_page(self):
        """Return the current page of the app."""
        return self.pages[self.current_page_id]

    @property
    def previous_page(self):
        """Return the current page of the app."""
        page_id = "BLANK"
        if len(self.page_stack) > 1:
            page_id = self.page_stack[-2]
        return self.pages[page_id]

    def initial_header_widget(self):
        """Initialize the header widget to be updated later."""
        return urwid.AttrWrap(
            urwid.Columns([
                urwid.Text(self.title, align='left'),
                urwid.AttrWrap(
                    urwid.Text(self.current_page.page_title, align='center'),
                    'important_header'
                ),
                urwid.Text(self.current_page.page_usage, align='right')
            ]),
            'header'
        )

    def initial_footer_widget(self):
        """Create the initial footer widget to be updated later."""
        return urwid.AttrWrap(
            urwid.Text(self.current_page.page_status, align='right'),
            'footer'
        )

    def add_page(self, page_id, page_cls, *args, **kwargs):
        """Instantiate a page to the app with a unique `page_id`."""
        assert page_id not in self.pages, "page ID must be unique"
        self.pages[page_id] = page_cls(self, *args, **kwargs)
        return self.pages[page_id]

    def set_page(self, page_id):
        """Add the page_id to the top of the page stack."""
        assert page_id in self.pages, "page ID must have been added."
        self.page_stack.append(page_id)

    def refresh_widgets(self, size):
        """Check before refreshing header / footer status widgets."""
        # TODO: update the text on the header / footer widgets with the latest
        # info from the current page app.
        self.current_page.refresh_widgets(size)
        current_page = self.current_page
        if self.body != current_page:
            self.body = current_page
        _, (wg_page_title, _), (wg_page_usage, _) = self.header.contents
        if wg_page_title.text != current_page.page_title:
            wg_page_title.set_text(current_page.page_title)
        if wg_page_usage.text != current_page.page_usage:
            wg_page_usage.set_text(current_page.page_usage)
        if self.footer.text != current_page.page_status:
            self.footer.text = current_page.page_status

    def _action_back(self, *_):
        """Go back to the previous page."""
        if self.page_stack:
            self.page_stack = self.page_stack[:-1]
        else:
            raise urwid.ExitMainLoop()

    def _action_error(self, *_):
        """Throw an error (for testing, remove later)."""
        self.modal_fatal_error("blah", "details")

    def keypress(self, size, key):
        """Wrap super `keypress`es and refresh body widget."""
        # always focussed on the body
        # self.body.keypress(size, key)
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)

    def render(self, size, focus=False):
        """Wrap super and mixin `render`s."""
        PKG_LOGGER.debug("current page is {}".format(self.current_page_id))
        self._mix_render(size, focus)

        if self.loop is not None:
            if self.current_page_id == 'BLANK':
                raise urwid.ExitMainLoop()

        return self.__super.render(size, focus)


class ZTVApp(with_metaclass(urwid.MetaSuper, urwid.MainLoop)):
    """Provide CLI app event loop functionality."""

    palette = [
        ('body', 'black', 'light gray', 'standout'),
        ('reverse', 'light gray', 'black'),
        ('column_header', 'dark blue', 'black', ('bold', 'underline')),
        ('column', 'light gray', 'black'),
        ('header', 'white', 'dark red', 'bold'),
        ('important_header', 'white', 'dark red', 'bold'),
        ('important', 'dark blue', 'light gray', ('standout', 'underline')),
        ('editfc', 'white', 'dark blue', 'bold'),
        ('editbx', 'light gray', 'dark blue'),
        ('editcp', 'black', 'light gray', 'standout'),
        ('footer', 'dark gray', 'light gray', ('bold', 'standout')),
        ('buttn', 'black', 'dark cyan'),
        ('buttnf', 'white', 'dark blue', 'bold'),
    ]

    def __init__(self, client=None, config=None):
        """
        Initialize ZTVApp instance.

        Args:
        ----
            client (:obj:`zenpy.Zenpy`): The Zendesk API client
        """
        self.config = config or configargparse.Namespace()
        self.screen = urwid.raw_display.Screen()
        self.frame = AppFrame(
            client=client, title=u"Zendesk Ticket Viewer", loop=self,
        )
        self.frame.add_page('WELCOME', WelcomePage)
        self.frame.add_page('TICKET_LIST', TicketListPage)
        self.frame.add_page('TICKET_VIEW', TicketViewPage)
        self.frame.set_page('WELCOME')
        if getattr(self.config, 'unpickle_tickets'):
            # no creds required when unpickle_tickets so bypass log in
            self.frame.pages['WELCOME']._action_login()
            del self.frame.pages['WELCOME']

        self.__super.__init__(
            widget=self.frame, palette=self.palette, screen=self.screen,
        )
