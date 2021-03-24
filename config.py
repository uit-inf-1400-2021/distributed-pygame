#!/usr/bin/env python3
"""
Common configuration for clients and the server.

It is also used to configure the logging level and output format for the logging library.
"""
import logging

# Select a port number that is unique for your group.
PORT = 32100
# Hostname of where you are running the server, or set to localhost for local development.
# SERVER = 'ifilab100.stud.cs.uit.no'
SERVER = 'localhost'

# Set up logging format and level
# See the documentation for more information:
# https://docs.python.org/3/library/logging.html
# https://docs.python.org/3/howto/logging.html
# DEBUG_LVL = logging.DEBUG
DEBUG_LVL = logging.INFO
logging.basicConfig(format='%(levelname)s:%(message)s', level=DEBUG_LVL)
