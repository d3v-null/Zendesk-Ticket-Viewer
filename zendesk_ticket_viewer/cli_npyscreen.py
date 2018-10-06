from builtins import super

import npyscreen
from npyscreen import TitleFixedText, TitlePager

from .core import LOG

ZENDESK_LOGO = """\
 `////////////////.  :///////////////.
  mNNNNNNNNNNNNNNN-  dNNNNNNNNNNNNNm/
  -mNNNNNNNNNNNNN+   dNNNNNNNNNNNNs`
   .smNNNNNNNNNh-    dNNNNNNNNNNh.
     `:+syyso/`  ::  dNNNNNNNNm/
               .yN+  dNNNNNNNo`
              +NNN+  dNNNNNh.
            :dNNNN+  dNNNm:
          .yNNNNNN+  dNNo`
        `oNNNNNNNN+  dy.     `
       :mNNNNNNNNN+  -  -ohmNNNmho-
     .hNNNNNNNNNNN+   -hNNNNNNNNNNNh-
   `oNNNNNNNNNNNNN+  -NNNNNNNNNNNNNNN-
  /mNNNNNNNNNNNNNN+  yNNNNNNNNNNNNNNNy\
"""

class TicketList(npyscreen.MultiLineAction):
    """A form widget that displays a list of tickets to be viewed."""

    # TODO: show header at top
    headers = {
        'id': ('Ticket #', )
    }

    def display_value(self, ticket):
        """Display a single ticket as a line."""
        fmt_params = ticket.to_dict().copy()
        # TODO: calculate max subject length from window size and trunc subject
        return "{id:5d} | '{subject}'".format(**fmt_params)

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.parentApp.getForm('VIEW_TICKET').value =act_on_this[0]
        self.parent.parentApp.switchForm('VIEW_TICKET')

class StatusWidget(npyscreen.MultiLine):
    pass

class TicketListDIsplay(npyscreen.FormMutt):
    # overrides
    MAIN_WIDGET_CLASS = TicketList
    STATUS_WIDGET_CLASS = StatusWidget

    # overrides
    def beforeEditing(self):
        self.update_list()
        self.wMain.values = self.parentApp.client.tickets()[:]

    def update_list(self):
        self.wMain.display()
        self.wStatus1.values = ["hi", "hi2"]
        self.wStatus2.values = ["hi", "hi2"]

class ViewTicket(npyscreen.ActionFormV2):
    def create(self):
        self.value = None
        self.wgTicketID      = self.add(TitleFixedText, name="Ticket #",)
        self.wgAssignee      = self.add(TitleFixedText, name="Assignee:")
        self.wgCCs           = self.add(TitleFixedText, name="CCs:")
        self.wgTags          = self.add(TitleFixedText, name="Tags:")
        self.wgType          = self.add(TitleFixedText, name="Type:")
        self.wgPriority      = self.add(TitleFixedText, name="Priority:")
        self.wgConversations = self.add(TitlePager, name="Conversations:")

class ZTVApp(npyscreen.NPSAppManaged):
    def __init__(self, client, *args, **kwargs):
        self.client = client
        super().__init__(*args, **kwargs)

    def onStart(self):
        self.addForm("MAIN", TicketListDIsplay)
        # self.addForm("VIEW_TICKET", EditRecord)
