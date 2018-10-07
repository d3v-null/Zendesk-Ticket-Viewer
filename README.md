[![Build Status](https://travis-ci.org/derwentx/Zendesk-Ticket-Viewer.svg?branch=master)](https://travis-ci.org/derwentx/Zendesk-Ticket-Viewer)
[![Maintainability](https://api.codeclimate.com/v1/badges/f72799f7d813f48f9329/maintainability)](https://codeclimate.com/github/derwentx/Zendesk-Ticket-Viewer/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/f72799f7d813f48f9329/test_coverage)](https://codeclimate.com/github/derwentx/Zendesk-Ticket-Viewer/test_coverage)

# Zendesk-Ticket-Viewer
A simple python CLI utility which views support tickets using the Zendesk API

# Installation

Install the `zendesk_ticket_viewer` console script to your path with

```bash
python setup.py install
```

Use develop instead of install if you would like make changes to this module.

# Testing

In order to perform tests, it is assumed that the account you are using has been
populated with the test data in `tests/test_data/tickets.json`. To populate
your test account with this data, you can use the script `populate_test_data.sh`

```bash
ZENDESK_SUBDOMAIN='subdomain' \
ZENDESK_EMAIL='email' \
ZENDESK_PASSWORD='password' \
tests/test_data/populate_test_data.sh tests/test_data/tickets.json
```

setup.py will use the tests directory to test the `zendesk_ticket_viewer` module.

```bash
python setup.py test
```

# Usage

Run the console utility with

```bash
zendesk_ticket_viewer \
    --subdomain '{subdomain}' \
    --email '{email}' \
    --password '{password}'
```

If you want to use the UI without an internet connection or login, you can load
a previously store session.

```bash
zendesk_ticket_viewer \
    --unpickle-tickets \
    --pickle-path 'tests/test_data/tickets.pkl'
```

# Roadmap
 - [x] make a barebones module which uses one of these clients https://developer.zendesk.com/rest_api/docs/api-clients/python
 - [x] *testing* - write skeleton of testing suite
 - [x] *testing* - automate tests on multiple Python versions with Travis / Codeclimate
 - [x] Validate API connection
 - [x] Implement logging
 - [x] simple proof of concept curses CLI using ~~npyscreen~~ urwid
 - [x] modularize multi-screen CLI code for easier testing
 - [x] beautiful error handing
 - [ ] welcome screen
 - [ ] *testing* - test coverage of CLI
 - [ ] *testing* - test on WSL
