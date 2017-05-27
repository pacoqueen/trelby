#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
exception classes
"""

class TrelbyError(Exception):
    """ General error. """
    def __init__(self, msg):
        """ Constructor """
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        """ String representation. """
        return str(self.msg)

class ConfigError(TrelbyError):
    """ Configuration error. """
    def __init__(self, msg):
        """ Constructor """
        TrelbyError.__init__(self, msg)

class MiscError(TrelbyError):
    """ Miscellaneous error. """
    def __init__(self, msg):
        """ Constructor. """
        TrelbyError.__init__(self, msg)
