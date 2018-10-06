"""
A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from io import open
from os import path

# Always prefer setuptools over distutils
from setuptools import setup

HERE = path.abspath(path.dirname(__file__))
PKG_NAME = 'zendesk_ticket_viewer'

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as readme_file:
    LONG_DESCRIPTION = readme_file.read()

VERSION = "0.1"
DESCRIPTION = (
    "A simple CLI utility which views support tickets using the Zendesk API"
)


setup(
    name=PKG_NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    url='https://github.com/derwentx/Zendesk-Ticket-Viewer',
    author='Derwent McElhinney',
    author_email='derwent@laserphile.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='ZenDesk Ticket',
    py_modules=[PKG_NAME],
    install_requires=[
        'zenpy',
        'configargparse',
        'requests',
        'urwid',
        'numpy',
    ],
    setup_requires=["pytest-runner"],
    tests_require=[
        'pytest',
        'coverage',
        'mock',
        'pytest-cov',
    ],
    entry_points={  # Creates a console script entry point on install
        'console_scripts': [
            '{0}={0}.core:main'.format(PKG_NAME),
        ],
    },
)
