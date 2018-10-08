import urwid


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


class FormFieldHorizontal(urwid.Columns):
    """A configurable widget which displays a field label and value."""

    _default_lbl_class = TicketCell
    _default_lbl_style = 'column_header'
    _default_val_class = urwid.Text
    _default_val_style = 'column'
    _default_val_kwargs = {}

    def __init__(self, field_label, field_value=None, *args, **kwargs):
        """
        Wrap super `__init__` with extra metadata and attributes.

        Args:
        ----
            key (:obj:`str`): The key into ticket data this field represents
        """
        self.key = kwargs.pop('key', None)
        self.field_label = field_label or ''
        self.field_value = field_value or ''

        self._lbl_class = kwargs.pop('lbl_class', self._default_lbl_class)
        self._lbl_style = kwargs.pop('lbl_style', self._default_lbl_style)
        self._val_class = kwargs.pop('val_class', self._default_val_class)
        self._val_style = kwargs.pop('val_style', self._default_val_style)
        self._val_kwargs = self._default_val_kwargs.copy()
        self._val_kwargs.update(kwargs.pop('val_kwargs', {}))

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
                    self._lbl_class(self.field_label, align=urwid.RIGHT),
                    self._lbl_style
                )
            ),
            (
                'weight', 2, urwid.AttrWrap(
                    self._val_class(self.field_value, **self._val_kwargs),
                    self._val_style
                )
            )
        ]

    def get_value_text(self):
        _, (wg_value, _) = self.contents
        return wg_value.text


class FormFieldHorizontalEdit(FormFieldHorizontal):
    _default_val_class = urwid.Edit


class FormFieldHorizontalPass(FormFieldHorizontalEdit):
    _default_val_kwargs = {'mask': '*'}

    def __init__(self, field_label, field_value, *args, **kwargs):
        """Wrap __init__ so field_value is edit_text, not caption."""
        kwargs['val_kwargs'] = {'edit_text': field_value or ''}
        field_value = ''
        self.__super.__init__(field_label, field_value, *args, **kwargs)

    def get_value_text(self):
        _, (wg_value, _) = self.contents
        old_mask = wg_value._mask
        wg_value.set_mask(None)
        response = self.__super.get_value_text()
        wg_value.set_mask(old_mask)
        return response
