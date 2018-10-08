"""Provide pages for Command line interface App."""

import functools

import numpy
import six
import urwid
from urwid.compat import with_metaclass

from ..core import PKG_LOGGER, get_client, validate_connection
from ..util import wrap_connection_error
from .widgets import (FormFieldHorizontal, FormFieldHorizontalEdit,
                      FormFieldHorizontalPass, TicketCell, TicketColumn)

ZENDESK_LOGO = \
    " `////////////////.  :///////////////.  \n" + \
    "  mNNNNNNNNNNNNNNN-  dNNNNNNNNNNNNNm/   \n" + \
    "  -mNNNNNNNNNNNNN+   dNNNNNNNNNNNNs`    \n" + \
    "   .smNNNNNNNNNh-    dNNNNNNNNNNh.      \n" + \
    "     `:+syyso/`  ::  dNNNNNNNNm/        \n" + \
    "               .yN+  dNNNNNNNo`         \n" + \
    "              +NNN+  dNNNNNh.           \n" + \
    "            :dNNNN+  dNNNm:             \n" + \
    "          .yNNNNNN+  dNNo`              \n" + \
    "        `oNNNNNNNN+  dy.     `          \n" + \
    "       :mNNNNNNNNN+  -  -ohmNNNmho-     \n" + \
    "     .hNNNNNNNNNNN+   -hNNNNNNNNNNNh-   \n" + \
    "   `oNNNNNNNNNNNNN+  -NNNNNNNNNNNNNNN-  \n" + \
    "  /mNNNNNNNNNNNNNN+  yNNNNNNNNNNNNNNNy\ "


class AppElementMixin(with_metaclass(urwid.MetaSuper)):
    """
    Functionality common to app elements.

    - Run `refresh_widgets` whenever `render` or `keypress` is called.
    - Handle events.
    """

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

    def _action_exit(self, *_):
        raise urwid.ExitMainLoop()

    def _get_markup(self, ticket_dict, key, formatter=None):
        formatter = formatter or id

        unformatted = ticket_dict.get(key, '')
        try:
            return formatter(unformatted)
        except UnicodeEncodeError:
            if not isinstance(unformatted, six.text_type):
                unformatted = six.text_type(unformatted)
            unformatted = (unformatted).encode('ascii', errors='ignore')
            return formatter(unformatted)

    def modal_fatal_error(self, message=None, exc=None):
        """Cause a fatal error to be displayed and the program to exit."""
        message = "Error: {}".format(message) if message else "Fatal Error"

        if message:
            PKG_LOGGER.critical(message)
        if exc:
            PKG_LOGGER.critical(exc)
        # This could be called from a parent frame or a page.
        parent_frame = getattr(self, 'parent_frame', self)
        if 'ERROR' not in parent_frame.pages:
            parent_frame.add_page('ERROR', ErrorPage)
        if message:
            parent_frame.pages['ERROR'].page_title = message

        details = []
        if exc:
            details.insert(0, str(exc))
        details.append("press ctrl-c to exit")
        parent_frame.pages['ERROR'].error_details = "\n\n".join(details)
        parent_frame.set_page('ERROR')


class AppPageMixin(AppElementMixin):
    """Provide the interface for a page within an app."""

    _usage = ""
    _title = ""

    def __init__(self):
        """Wrap super __init__ as per `urwid.MetaClass` spec."""
        assert self.parent_frame
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

    def __init__(self, parent_frame, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        self.parent_frame = parent_frame
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

    def __init__(self, parent_frame, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        # Cache access to generator to avoid api calls
        self._ticket_cache = []
        # Offset into the generator of the first visible element
        self.offset = 0
        # Index of the highlighted element
        self.index_highlighted = 0
        # Force a space of 1 between columns
        kwargs['dividechars'] = 0
        self.parent_frame = parent_frame
        self._ticket_generator = None
        self.__super.__init__(
            self.initial_column_widgets(), *args, **kwargs
        )

    @property
    def ticket_generator(self):
        """Try and get generator of tickets from API otherwise use cache."""
        if self._ticket_generator is not None:
            return self._ticket_generator

        client = self.parent_frame.client
        cache = client.tickets.cache.mapping['ticket'].cache
        # if we are in offline mode

        if cache.__class__.__name__ != 'TTLCache':
            self._ticket_generator = cache.values().__iter__()
        else:
            self._ticket_generator = wrap_connection_error(
                functools.partial(client.tickets, timeout=5),
                attempting="Connecting to API",
                on_fail=functools.partial(self.modal_fatal_error),
                on_success=functools.partial(
                    PKG_LOGGER.info, "Connected to API"
                )
            )
        # assert self._ticket_generator, \
        #     "failure to make generator should be caught"
        return self._ticket_generator

    @property
    def next_ticket(self):
        # get before wrap so that we don't wrap twice
        generator = self.ticket_generator
        if generator is None:
            # want to exit getting ticket_generator cleanly in case there
            # was an error that needs to be displayed
            raise StopIteration()
        response = wrap_connection_error(
            injected=functools.partial(next, generator),
            attempting="Making an API request",
            on_fail=functools.partial(self.modal_fatal_error),
        )
        if response is None:
            raise StopIteration()
        return response

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
        for key, meta in self.parent_frame.column_meta.items():
            if 'list_view' in meta and not meta['list_view']:
                continue
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
            while self.ticket_generator is not None:
                if prefetch_index < len(self._ticket_cache):
                    break
                self._ticket_cache.append(self.next_ticket)
        except StopIteration:
            pass
        return self._ticket_cache[offset:offset + limit]

    def _get_cell_widgets(self, key, visible_tickets, index_highlighted):
        meta = self.parent_frame.column_meta.get(key, {})
        formatter = meta.get('formatter', str)
        cell_kwargs = {
            'align': meta.get('align', urwid.LEFT)
        }
        cell_widgets = []
        for index, ticket in enumerate(visible_tickets):
            cell_kwargs['markup'] = self._get_markup(
                ticket.to_dict(), key, formatter
            )
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
        self._action_scroll(size)

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
            max(len(self._ticket_cache) - 1, 0)
        )

    def _action_open(self, *_):
        """Open view of selected ticket."""
        ticket = self._ticket_cache[self.offset + self.index_highlighted]
        PKG_LOGGER.debug('Actioning ticket id={}'.format(ticket))
        if 'TICKET_VIEW' not in self.parent_frame.pages:
            self.parent_frame.add_page(TicketViewPage)
        self.parent_frame.pages['TICKET_VIEW'].current_ticket = ticket
        self.parent_frame.set_page('TICKET_VIEW')

    def keypress(self, size, key):
        """Wrap super `keypress` and perform actions / scroll."""
        # Scroll regardless of if a move was made
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)

    def render(self, size, focus=False):
        """Wrap super and mixin `render`s."""
        self._mix_render(size, focus)
        return self.__super.render(size, focus)


class TicketViewPage(urwid.ListBox, AppPageMixin):
    """An app page which displays a single ticket's information."""

    _usage = (
        u"ESC is back. "
        u"F8 exits."
    )
    _title = "Ticket View"

    def __init__(self, parent_frame, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        self.parent_frame = parent_frame
        self.current_ticket = None
        self.__super.__init__(urwid.SimpleListWalker(
            self.initial_row_widgets()
        ))

    def initial_row_widgets(self):
        """Initialize the row widgets to be updated later."""
        widget_list = []

        for key, meta in self.parent_frame.column_meta.items():
            field_label = meta.get('title', key.title())
            field_class = meta.get('field_class', FormFieldHorizontal)
            widget_list.append(field_class(field_label, key=key))

        return widget_list

    def refresh_widgets(self, size):
        """Refresh the row widgets."""
        ticket_dict = {}
        if self.current_ticket:
            ticket_dict = self.current_ticket.to_dict()

        for wg_field in self.body.contents:
            meta = self.parent_frame.column_meta.get(wg_field.key, {})
            _, (wg_field_value, _) = wg_field.contents
            formatter = meta.get('formatter', str)
            markup = self._get_markup(ticket_dict, wg_field.key, formatter)
            if wg_field_value.text != markup:
                wg_field_value.set_text(markup)

    def keypress(self, size, key):
        """Wrap super `keypress`es."""
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)

    def render(self, size, focus=False):
        """Wrap super and mixin `render`s."""
        self._mix_render(size, focus)
        return self.__super.render(size, focus)


class ErrorPage(urwid.Overlay, AppPageMixin):
    """An app page which displays an error."""
    _usage = (
        u"F8 / ESC exits."
    )

    key_actions = {
        'f8': 'exit',
        'esc': 'exit',
        'ctrl c': 'exit',
    }

    def __init__(self, parent_frame, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        self.parent_frame = parent_frame
        self._title = kwargs.get('error_message', 'Error')
        self.error_details = kwargs.get('error_details', 'An Error occured.')

        # popup = urwid.Text(self.error_message)
        self.__super.__init__(
            urwid.AttrWrap(
                urwid.LineBox(
                    urwid.ListBox(urwid.SimpleFocusListWalker([
                        urwid.Divider(),
                        urwid.Text(self.error_details, align='center')
                    ])),
                    title=self.page_title
                ),
                'header'
            ),
            self.parent_frame.current_page,
            align='center', width=('relative', 50),
            valign='middle', height=('relative', 50),
            min_width=24, min_height=8,
        )

    @AppPageMixin.page_title.setter
    def page_title(self, value):
        self._title = value

    def refresh_widgets(self, *_):
        _, (wg_top, _) = self.contents
        wg_title = wg_top.original_widget.title_widget
        if wg_title.text != self.page_title:
            wg_title.set_text(self.page_title)
        wg_details = wg_top.original_widget.original_widget.body[1]
        if wg_details.text != self.error_details:
            wg_details.set_text(self.error_details)

    def render(self, size, focus=False):
        """Wrap super and mixin `render`s."""
        self._mix_render(size, focus)
        return self.__super.render(size, focus)

    def keypress(self, size, key):
        """Wrap super `keypress`."""
        # Scroll regardless of if a move was made
        self._mix_keypress(size, key)
        self.__super.keypress(size, key)


class WelcomePage(urwid.Overlay, AppPageMixin):
    _title = "Welcome"

    key_actions = {
        'enter': 'login'
    }

    _usage = (
        u"F8 / ESC exits."
    )

    def __init__(self, parent_frame, *args, **kwargs):
        """Wrap super `__init__` with extra metadata."""
        self.parent_frame = parent_frame
        config = self.parent_frame.config
        self.form_fields = [
            cls(label_text, getattr(config, key, ''), key=key)
            for key, (cls, label_text) in {
                'subdomain': (FormFieldHorizontalEdit, 'Subdomain: '),
                'email': (FormFieldHorizontalEdit, 'Email: '),
                'password': (FormFieldHorizontalPass, 'Password: '),
            }.items()
        ]

        widget_list = [
            urwid.Divider(),
            urwid.Text(ZENDESK_LOGO, align='center'),
            urwid.Divider(),
        ] + self.form_fields + [
            urwid.Divider(),
            urwid.Button(
                "Login", on_press=self._action_login
            )
        ]

        self.__super.__init__(
            urwid.AttrWrap(
                urwid.LineBox(
                    urwid.ListBox(urwid.SimpleFocusListWalker(
                        widget_list
                    )),
                ),
                'column_header'
            ),
            self.parent_frame.current_page,
            align='center', width=('relative', 50),
            valign='middle', height=('relative', 80),
            min_width=24, min_height=8,
        )

    def _action_login(self, *args):
        for wg_field in self.form_fields:
            value = wg_field.get_value_text()
            setattr(
                self.parent_frame.config, wg_field.key, value
            )
            if wg_field.key == 'password':
                value = "*" * len(value)
            PKG_LOGGER.info("updated config[{}] = {}".format(
                wg_field.key, value
            ))

        # The Ticket Viewer should handle the API being unavailable
        wrap_connection_error(
            functools.partial(validate_connection, self.parent_frame.config),
            attempting="Validate connection",
            on_fail=functools.partial(self.modal_fatal_error),
            on_success=functools.partial(
                PKG_LOGGER.info, "Connection validated"
            )
        )

        self.parent_frame.client = wrap_connection_error(
            functools.partial(get_client, self.parent_frame.config),
            attempting="Create client",
            on_fail=functools.partial(self.modal_fatal_error),
            on_success=functools.partial(
                PKG_LOGGER.info, "Client created"
            )
        )

        # if no error screen is showing
        if self.parent_frame.current_page_id == 'WELCOME':
            self.parent_frame.set_page('TICKET_LIST')
