import logging
from builtins import super
from collections import OrderedDict

import urwid
import numpy

from . import PKG_NAME

PKG_LOGGER = logging.getLogger(PKG_NAME)


class TicketCell(urwid.Text):
    def __init__(self, *args, **kwargs):
        # Force clipping on cell elements
        kwargs['wrap'] = urwid.CLIP
        super().__init__(*args, **kwargs)

class TicketColumn(urwid.Frame):
    def __init__(self, body, header=None, *args, **kwargs):
        # The key which this column is associated with
        self.key = kwargs.pop('key')
        if body is not None:
            body = urwid.AttrWrap(body, 'column')
        if header is not None:
            header = urwid.AttrWrap(header, 'column_header')
        super().__init__(body, header, *args, **kwargs)

class TicketList(urwid.Columns):
    _selectable = True
    header_size = 1
    # change this to change how quickly the scrolls when paging
    page_speed = 1

    column_meta = OrderedDict([
        ('id', {
            'title': 'Ticket #',
            'sizing': ['fixed', 9],
            'align': 'right'
        }),
        ('subject', {}),
        ('type', {
            'formatter': (lambda x: (x or 'ticket').title() )
        }),
        ('priority', {
            'formatter': (lambda x: x or '-')
        }),
    ])

    def __init__(self, client, *args, **kwargs):
        self.client = client
        self.ticket_generator = self.client.tickets()
        # Cache access to generator to avoid api calls
        self._ticket_cache = []
        # Offset into the generator of the first visible element
        self.offset = 0
        # Index of the highlighted element
        self.index_highlighted = 0
        super().__init__(self.initial_widget_list(), *args, **kwargs)
        # Refresh widgets as if there was room for 1 row.
        self.refresh_widgets((None,self.header_size+1))

    def initial_widget_list(self):
        """
        Generated the initial list of column widgets.

        Widget size is not known until render time, so no ticket entries are
        added to the widget list initially.
        """

        # TODO: add footer widget that shows paging progress ("X - Y of Z")
        widget_list = []
        for key, meta in self.column_meta.items():
            title = meta.get('title', key.title())
            column_widget = TicketColumn(
                header=TicketCell(title),
                body=urwid.ListBox(urwid.SimpleListWalker([
                    # TicketCell("row 1"),
                    # urwid.AttrWrap(TicketCell("row 2"), 'important'),
                    # TicketCell("row 3"),
                    # TicketCell("row 4"),
                ])),
                key=key
            )
            if 'sizing' in meta:
                column_widget = tuple(
                    meta['sizing'] + [column_widget]
                )
            widget_list.append(column_widget)

        return widget_list

    def get_tickets(self, offset, limit=None):
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
                if limit is not None \
                and prefetch_index < len(self._ticket_cache):
                    break
                self._ticket_cache.append(self.ticket_generator.next())
        except StopIteration:
            pass
        if limit is not None:
            return self._ticket_cache[offset:offset+limit]
        return self._ticket_cache[offset:]

    def refresh_widgets(self, size):
        """
        Populate frame body of each column with visible tickets
        """
        _, maxcol = size
        visible_tickets = self.get_tickets(self.offset, maxcol-self.header_size)
        # TODO: populate frame body of each column with visible tickets
        for column, _ in self.contents:
            formatter = self.column_meta[column.key].get('formatter', str)
            cell_widgets = [
                TicketCell(formatter(ticket.to_dict().get(column.key, ''))) \
                for ticket in visible_tickets
            ]
            cell_widgets[self.index_highlighted] = urwid.AttrWrap(
                cell_widgets[self.index_highlighted], 'important'
            )
            # TODO: test for memory usage

            # cell_widgets = []
            # for index, ticket in enumerate(visible_tickets):
            #     import pudb; pudb.set_trace()
            #     cell_widget = TicketCell(str(ticket.to_dict().get(column.key, '')))
            #     if index == self.index_highlighted:
            #         cell_widget = urwid.AttrWrap(cell_widget, 'important')
            #     cell_widgets.append(cell_widget)

            column.body = urwid.ListBox(urwid.SimpleListWalker(cell_widgets))


    def scroll(self, size, movement):
        """
        Move highlighted index by `movement`, scroll `offset` at boundaries.

        Even if movement is 0 it is useful to refresh these values since the
        widget can be resized.
        """
        _, maxcol = size
        # move highlighted index until boundaries
        can_move_to = numpy.clip(
            self.index_highlighted + movement,
            0,
            maxcol - self.header_size
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

        self.refresh_widgets(size)

    def render(self, size, focus=False):
        PKG_LOGGER.debug('rendering, size={} focus={}'.format(size, focus))
        self.scroll(size, 0)
        if hasattr(super(), 'render'):
            return super().render(size, focus)

    def _action_open(self):
        """Open view of selected ticket."""
        ticket_id = self._ticket_cache[self.offset + self.index_highlighted]
        PKG_LOGGER.debug('Actioning ticket id={}'.format(ticket_id))

    def keypress(self, size, key):
        PKG_LOGGER.debug('keypress, size={} key={}'.format(size, repr(key)))
        _, maxcol = size
        # TODO: action selected ticket when key
        key_actions = {
            ' ': 'open',
            'enter': 'open',
        }
        if key in key_actions:
            getattr(self, '_action_{}'.format(key_actions[key]))()

        # Map key value to scroll movement amount
        key_movements = {
            'up': -1,
            'down': 1,
            'page up': int(self.page_speed * (maxcol - self.header_size)),
            'page down': int(self.page_speed * (self.header_size - maxcol))
        }
        self.scroll(size, key_movements.get(key, 0))
        return super().keypress(size, key)

class ZTVApp(object):
    title = u"Zendesk Ticket Viewer"
    def __init__(self, client):
        self.client = client

    def run(self):

        PKG_LOGGER.debug('Running TUI App')

        text_header_left = self.title
        text_header_center = [
            ('important_header', "Ticket List ")
        ]
        text_header_right = [
            u"UP / DOWN / PAGE UP / PAGE DOWN scrolls. SPACE / ENTER selects. F8 exits."
        ]

        blank = urwid.Divider()

        header = urwid.AttrWrap(
            urwid.Columns([
                urwid.Text(text_header_left, align='left'),
                urwid.Text(text_header_center, align='center'),
                urwid.Text(text_header_right, align='right')
            ]),
            'header'
        )

        # TODO: finish this

        body = TicketList(self.client)

        frame = urwid.Frame(
            header=header,
            body=body,
            footer=blank
        )

        palette = [
            ('body','black','light gray', 'standout'),
            ('reverse','light gray','black'),
            ('column_header','dark blue','black', ('bold', 'underline')),
            ('column','light gray','black'),
            ('header','white','dark red', 'bold'),
            ('important_header','dark blue', 'dark red', 'bold'),
            ('important','dark blue','light gray',('standout','underline')),
            ('editfc','white', 'dark blue', 'bold'),
            ('editbx','light gray', 'dark blue'),
            ('editcp','black','light gray', 'standout'),
            ('bright','dark gray','light gray', ('bold','standout')),
            ('buttn','black','dark cyan'),
            ('buttnf','white','dark blue','bold'),
        ]

        screen = urwid.raw_display.Screen()

        def unhandled(key):
            if key == 'f8':
                raise urwid.ExitMainLoop()

        urwid.MainLoop(
            frame, palette, screen,
            unhandled_input=unhandled
        ).run()
