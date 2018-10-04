# Zendesk-Ticket-Viewer
A simple python CLI utility which views support tickets using the Zendesk API

# Testing

TODO

# Installation

Install the `zendesk_ticket_viewer` console script to your path with

```bash
python setup.py install
```

# Usage

Run the console utility with

```bash
zendesk_ticket_viewer \
    --subdomain '{subdomain}' \
    --email '{email}' \
    --password '{password}'
```

# Roadmap
 - [x] make a barebones module which uses one of these clients https://developer.zendesk.com/rest_api/docs/api-clients/python
 - [ ] *testing* - write skeleton of testing suite
 - [ ] *testing* - automate tests on multiple OS / Python versions with Travis
 - [ ] build curses CLI using npyscreen
 - [ ] *testing* - full coverage of functions called by CLI
 - [ ] *testing* - (time-dependent) full coverage of curses interface by injecting stdin of a subprocess
