[![Build Status](https://travis-ci.org/derwentx/Zendesk-Ticket-Viewer.svg?branch=master)](https://travis-ci.org/derwentx/Zendesk-Ticket-Viewer)
[![Maintainability](https://api.codeclimate.com/v1/badges/f72799f7d813f48f9329/maintainability)](https://codeclimate.com/github/derwentx/Zendesk-Ticket-Viewer/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/f72799f7d813f48f9329/test_coverage)](https://codeclimate.com/github/derwentx/Zendesk-Ticket-Viewer/test_coverage)

# Zendesk-Ticket-Viewer
A simple python CLI utility which views support tickets using the Zendesk API

# Installation

## Widnows

In order to run this on Windows you will need to install either [windodows subsystem for linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10) if you have windows 10 or newer, or [cygwin](https://cygwin.com/install.html)

It is recommended (although not completely necessary) that you use a terminal that supports UTF-8 and colour like [cmder](https://github.com/cmderdev/cmder)

## Any other OS

Ensure you have python, pip and setuptools on your machine (this works on either Python2 or 3 so choose whatever version you prefer):

```bash
sudo apt-get update && sudo apt-get install python python-pip setuptools
```

Install the `zendesk_ticket_viewer` console script to your path with

```bash
python setup.py install
```

Note: you may need to `pip install . --user` if you get a permission error.

Replace `install` with  `develop` instead of install if you would like make changes to this module that will be take affect right away.

# Testing

In order to perform tests, it is a good idea to populate a tst Zendesk account with the data `tests/test_data/tickets.json`. To do this, you can use the script `populate_test_data.sh`

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

# Features

## Ticket List
<img src="screenshots/ticket_list.png?raw=true">

## Single Ticket View
<img src="screenshots/ticket_view.png?raw=true">

## Nice Error Messages
<img src="screenshots/error.png?raw=true">

## Emoji Support
<img src="screenshots/emoji_support.png?raw=true">

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
