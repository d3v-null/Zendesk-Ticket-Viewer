"""
Provide Command Line Interface for the package using the urwid library.

TODO: split this module into cli.widgets, cli.pages, cli.app to fix
    https://github.com/derwentx/Zendesk-Ticket-Viewer/issues/2
"""

import logging
from collections import OrderedDict

import numpy
import urwid
from urwid.compat import with_metaclass

from . import PKG_NAME

PKG_LOGGER = logging.getLogger(PKG_NAME)


class TicketCell(urwid.Text):
    """A widget forming a cell within a table of ticket information."""

    def __init__(self, *args, **kwargs):
        """Wrap super `__init__`, force clipping on cell elements."""
        kwargs['wrap'] = urwid.CLIP
        self.__super.__init__(*args, **kwargs)


class TicketColumn(urwid.Frame):
    """A widget forming a column within a table of ticket information."""

    def __init__(self, body, header=None, *args, **kwargs):
        """
        Wrap super `__init__` with extra metadata and attributes.

        Args:
        ----
            key (:obj:`str`): The key into ticket data this column represents
        """
        # The key which this column is associated with
        self.key = kwargs.pop('key', None)
        if body is not None:
            body = urwid.AttrWrap(body, 'column')
        if header is not None:
            header = urwid.AttrWrap(header, 'column_header')

        self.__super.__init__(body, header, *args, **kwargs)


class TicketFieldHorizontal(urwid.Columns):
    """A widget which displays a ticket field title and contents."""

    def __init__(self, field_name, field_value=None, *args, **kwargs):
        """
        Wrap super `__init__` with extra metadata and attributes.

        Args:
        ----
            key (:obj:`str`): The key into ticket data this field represents
        """
        self.key = kwargs.pop('key', None)
        self.field_name = field_name
        self.field_value = field_value
        kwargs['dividechars'] = 1
        self.__super.__init__(
            self.initial_widget_list(),
            *args, **kwargs
        )

    def initial_widget_list(self):
        """Initialize child widgets without no knowlodge of contents."""
        return [
            (
                'weight', 1, urwid.AttrWrap(
                    TicketCell(self.field_name, align=urwid.RIGHT),
                    'column_header'
                )
            ),
            (
                'weight', 2, urwid.AttrWrap(
                    TicketCell(self.field_value or '', ),
                    'editbx'
                )
            )
        ]


class RefreshesWidgetsMixin(with_metaclass(urwid.MetaSuper)):
    """Refresh Widgets whenever `render` or `keypress` is called."""

    # A mapping of keys to actions (override this).
    key_actions = {}

    def refresh_widgets(self, size):
        pass

    def _mix_render(self, size, focus=False):
        """Wrap super `render` to refresh widgets."""
        PKG_LOGGER.debug('{} rendering, size={} focus={}'.format(
            self.__class__.__name__, size, focus
        ))
        self.refresh_widgets(size)

    def _mix_keypress(self, size, key):
        """Wrap super `keypress` to refresh widgets."""
        PKG_LOGGER.debug('{} keypress, size={} key={}'.format(
            self.__class__.__name__, size, repr(key)
        ))

        # TODO: replace logic with urwid.command_map ?

        if key in self.key_actions:
            getattr(self, '_action_{}'.format(self.key_actions[key]))(
                size, key
            )

        self.refresh_widgets(size)


class AppPageMixin(RefreshesWidgetsMixin):
    """Provide the interface for a page within an app."""

    _usage = ""
    _title = ""

    def __init__(self):
        """Wrap super __init__ as per `urwid.MetaClass` spec."""
        assert self.parent_app
        self.__super.__init__()

    @property
    def page_usage(self):
        """Provide the usage message for this page."""
        return self._usage

    @property
    def page_title(self):
        """Provide the title for this page."""
        return self._title

    @property
    def page_status(self):
        """Provide an optional status line for this page."""
        return ""


class BlankPage(urwid.ListBox, AppPageMixin):
    """A blank app page."""

    def __init__(self, parent_app, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        self.parent_app = parent_app
        self.__super.__init__(urwid.SimpleListWalker([]))


class TicketListPage(urwid.Columns, AppPageMixin):
    """An app page which displays a table of ticket information."""

    _selectable = True
    header_size = 1
    footer_size = 0
    # how quickly the scrolls when paging
    page_speed = 1
    _usage = (
        u"UP / DOWN / PAGE UP / PAGE DOWN scrolls. "
        u"SPACE / ENTER selects. "
        u"F8 exits."
    )
    _title = "Ticket List"

    key_actions = {
        ' ': 'open',
        'enter': 'open',
        'up': 'scroll',
        'down': 'scroll',
        'page up': 'scroll',
        'page down': 'scroll',
    }

    def __init__(self, parent_app, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        # Cache access to generator to avoid api calls
        self._ticket_cache = []
        # Offset into the generator of the first visible element
        self.offset = 0
        # Index of the highlighted element
        self.index_highlighted = 0
        # Force a space of 1 between columns
        kwargs['dividechars'] = 0
        self.parent_app = parent_app
        self.ticket_generator = self.parent_app.client.tickets()
        self.__super.__init__(
            self.initial_column_widgets(), *args, **kwargs
        )

        # Refresh widgets as if there was room for 1 row (otherwise blank).
        # HACK: find a more elegant solution for this
        self.refresh_widgets((None, self.nonbody_overhead + 1))

    @property
    def nonbody_overhead(self):
        """Rows taken up by the header and footer."""
        return self.header_size + self.footer_size

    @AppPageMixin.page_status.getter
    def page_status(self):
        """Provide the status message for this page."""
        # TODO: paging progress ("X - Y of Z")
        return ""

    def initial_column_widgets(self):
        """
        Generate the initial list of column widgets.

        Widget size is not known until render time, so no ticket entries are
        added to the widget list initially.
        """
        # First column is a selection indicator
        widget_list = [
            ('fixed', 1, TicketColumn(
                header=urwid.Divider(),
                body=urwid.Divider(),
                key='_selected'
            ))
        ]
        # Other widget columns show ticket data
        for key, meta in self.parent_app.column_meta.items():
            title = meta.get('title', key.title())
            column_widget = TicketColumn(
                header=TicketCell(title),
                body=urwid.ListBox(urwid.SimpleListWalker([])),
                key=key
            )
            if 'sizing' in meta:
                column_widget = tuple(meta['sizing'] + [column_widget])
            widget_list.append(column_widget)

        return widget_list

    def get_tickets(self, offset, limit):
        """
        Fetch `limit` tickets from the generator starting at `offset`.

        Prefetch and cache 2 * `limit` tickets from the API.

        Args
        ----
            offset (:obj:`int`): the index of the first ticket required
            limit (:obj:`int`): the number of tickets required
        """
        prefetch_index = 2 * (limit) + offset

        try:
            while True:
                if prefetch_index < len(self._ticket_cache):
                    break
                self._ticket_cache.append(next(self.ticket_generator))
        except StopIteration:
            pass
        return self._ticket_cache[offset:offset + limit]

    def _get_cell_widgets(self, key, visible_tickets, index_highlighted):
        meta = self.parent_app.column_meta.get(key, {})
        formatter = meta.get('formatter', str)
        cell_kwargs = {
            'align': meta.get('align', urwid.LEFT)
        }
        cell_widgets = []
        for index, ticket in enumerate(visible_tickets):
            cell_kwargs['markup'] = formatter(ticket.to_dict().get(key, ''))
            if key == '_selected' and index == index_highlighted:
                cell_kwargs['markup'] = '>'
            cell_widget = TicketCell(**cell_kwargs)
            if index == index_highlighted:
                cell_widget = urwid.AttrWrap(cell_widget, 'important')
            cell_widgets.append(cell_widget)
        return cell_widgets

    def refresh_widgets(self, size):
        """
        Populate frame body of each column with visible tickets.

        Args
        ----
            size (:obj:`tuple` of :obj:`int`): The allowed size of the widget

        """
        PKG_LOGGER.debug('refreshing, size={}'.format(size))
        self._action_scroll(size, None)

        _, maxcol = size
        visible_tickets = self.get_tickets(
            self.offset, maxcol - self.nonbody_overhead
        )
        index_highlighted = numpy.clip(
            self.index_highlighted,
            0,
            min(maxcol - self.nonbody_overhead, len(visible_tickets)) - 1
        )

        for column, _ in self.contents:
            cell_widgets = self._get_cell_widgets(
                column.key, visible_tickets, index_highlighted
            )

            # TODO: test for memory leaks

            column.body = urwid.ListBox(urwid.SimpleListWalker(cell_widgets))

    def _action_scroll(self, size, key=None):
        """
        Move highlighted index by `movement`, scroll `offset` at boundaries.

        Even if movement is 0 it is useful to refresh these values since the
        widget can be resized.
        """
        PKG_LOGGER.debug('scrolling, size={} key={}'.format(
            size, key
        ))
        _, maxcol = size
        # Map key value to scroll movement amount
        page_jump = int(self.page_speed * (maxcol - self.nonbody_overhead))
        key_movements = {
            'up': -1,
            'down': 1,
            'page up': -page_jump,
            'page down': page_jump
        }
        movement = key_movements.get(key, 0)
        # move highlighted index until boundaries
        can_move_to = numpy.clip(
            self.index_highlighted + movement,
            0,
            maxcol - self.nonbody_overhead - 1
        )
        # determine remaining movement to potentially move the offset
        movement = movement - (can_move_to - self.index_highlighted)
        self.index_highlighted = can_move_to

        # offset can't exceed ticket cache
        self.offset = numpy.clip(
            self.offset + movement,
            0,
            len(self._ticket_cache) - 1
        )

    def _action_open(self, *_):
        """Open view of selected ticket."""
        ticket = self._ticket_cache[self.offset + self.index_highlighted]
        PKG_LOGGER.debug('Actioning ticket id={}'.format(ticket))
        if 'TICKET_VIEW' not in self.parent_app.pages:
            self.parent_app.add_page(TicketViewPage)
        self.parent_app.pages['TICKET_VIEW'].current_ticket = ticket
        self.parent_app.set_page('TICKET_VIEW')

    def keypress(self, size, key):
        """Wrap super `keypress` and perform actions / scroll."""
        # Scroll regardless of if a move was made
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)

    def render(self, size, focus=False):
        """Wrap super `render`s to refresh scroll."""
        self._mix_render(size, focus)
        return self.__super.render(size, focus)


class TicketViewPage(urwid.ListBox, AppPageMixin):
    """An app page which displays a single ticket's information."""

    _usage = (
        u"UP / DOWN / PAGE UP / PAGE DOWN scrolls. "
        u"F8 exits."
    )
    _title = "Ticket View"

    def __init__(self, parent_app, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        self.parent_app = parent_app
        self.current_ticket = None
        self.__super.__init__(urwid.SimpleListWalker(
            self.initial_row_widgets()
        ))

    def initial_row_widgets(self):
        """Initialize the row widgets to be updated later."""
        widget_list = []

        for key, meta in self.parent_app.column_meta.items():
            field_name = meta.get('title', key.title())
            field_class = meta.get('field_class', TicketFieldHorizontal)
            widget_list.append(field_class(field_name, key=key))

        return widget_list

    def refresh_widgets(self, size):
        """Refresh the row widgets."""
        ticket_dict = {}
        if self.current_ticket:
            ticket_dict = self.current_ticket.to_dict()

        for wg_field in self.body.contents:
            meta = self.parent_app.column_meta.get(wg_field.key, {})
            _, (wg_field_value, _) = wg_field.contents
            formatter = meta.get('formatter', str)
            markup = formatter(ticket_dict.get(wg_field.key, ''))
            if wg_field_value.text != markup:
                wg_field_value.set_text(markup)

    def keypress(self, size, key):
        """Wrap super `keypress`es."""
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)

    def render(self, size, focus=False):
        """Wrap super `render`s."""
        self._mix_render(size, focus)
        return self.__super.render(size, focus)


class AppFrame(urwid.Frame, RefreshesWidgetsMixin):
    """Provide a Frame widget to house a multi-page app."""

    column_meta = OrderedDict([
        ('id', {
            'title': 'Ticket #',
            'sizing': ['fixed', 9],
            'align': 'right',
            'formatter': (lambda x: " {} ".format(x))
        }),
        ('subject', {
            'sizing': ['weight', 2],
        }),
        ('type', {
            'formatter': (lambda x: (x or 'ticket').title())
        }),
        ('priority', {
            'formatter': (lambda x: x or '-')
        }),
    ])

    key_actions = {
        'esc': 'back',
    }

    def __init__(self, title=None, client=None, *args, **kwargs):
        """Wrap super __init__ with extra meta."""
        self.title = title or ''
        # Mapping of pageIDs to widgets
        self.pages = {
            'BLANK': BlankPage(self)
        }
        # LIFO queue of page IDs that functions as a "history".
        self.page_stack = []
        # API Client,
        self.client = client
        # TODO: figure outo what to pass to super Frame __init__
        self.__super.__init__(
            header=self.initial_header_widget(),
            body=self.current_page,
            footer=self.initial_footer_widget(),
            *args, **kwargs
        )

    @property
    def current_page(self):
        """Return the current page of the app."""
        page_id = "BLANK"
        if self.page_stack:
            page_id = self.page_stack[-1]
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

    def keypress(self, size, key):
        """Wrap super `keypress`es and refresh body widget."""
        # always focussed on the body
        # self.body.keypress(size, key)
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)

    def render(self, size, focus=False):
        """Wrap super `render`s."""
        self._mix_render(size, focus)
        return self.__super.render(size, focus)


class ZTVApp(object):
    """Provide CLI app functionality."""

    def __init__(self, client):
        """
        Initialize ZTVApp instance.

        Args:
        ----
            client (:obj:`zenpy.Zenpy`): The Zendesk API client
        """
        self.client = client

    def run(self):
        """Start the TUI app."""
        PKG_LOGGER.debug('Running TUI App')

        frame = AppFrame(client=self.client, title=u"Zendesk Ticket Viewer")
        frame.add_page('TICKET_LIST', TicketListPage)
        frame.add_page('TICKET_VIEW', TicketViewPage)
        frame.set_page('TICKET_LIST')

        palette = [
            ('body', 'black', 'light gray', 'standout'),
            ('reverse', 'light gray', 'black'),
            ('column_header', 'dark blue', 'black', ('bold', 'underline')),
            ('column', 'light gray', 'black'),
            ('header', 'white', 'dark red', 'bold'),
            ('important_header', 'dark blue', 'dark red', 'bold'),
            (
                'important', 'dark blue', 'light gray',
                ('standout', 'underline')
            ),
            ('editfc', 'white', 'dark blue', 'bold'),
            ('editbx', 'light gray', 'dark blue'),
            ('editcp', 'black', 'light gray', 'standout'),
            ('footer', 'dark gray', 'light gray', ('bold', 'standout')),
            ('buttn', 'black', 'dark cyan'),
            ('buttnf', 'white', 'dark blue', 'bold'),
        ]

        screen = urwid.raw_display.Screen()

        def unhandled(key):
            if key == 'f8':
                raise urwid.ExitMainLoop()

        urwid.MainLoop(
            frame, palette, screen,
            unhandled_input=unhandled
        ).run()
