#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 tw=100 et ai si
#
# Copyright (c) 2013-2015 Intel, Inc.
# License: GPLv2
# Author: Andy Shevchenko <andriy.shevchenko@linux.intel.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

"""
Transport interface class to an instrument. This layer provides basic functions to communicate with
the instrument, such as 'read()' and 'write()'.

Currently, only the USBTMC transport is supported.
"""

import os
import logging
from fcntl import ioctl

class Error(Exception):
    """A class for exceptions generated by this module."""
    pass

class _Transport(object):
    """Virtual base class for the transport interface."""

    def __init__(self):
        """The virtual base class constructor."""

        self._name = self.__class__.__name__
        self._log = logging.getLogger(self._name)

    def _dbg(self, message): # pylint: disable=no-self-use
        """Print a debug message."""
        self._log.debug("%s", message.rstrip())

    def read(self, size):
        """Read from the transport interface."""
        raise Error("read(%s) method should be implemented in %s class" % (size, self._name))

    def write(self, data):
        """Write an arbitrary 'data' to the transport interface."""
        raise Error("write(%d) method should be implemented in %s class" % (len(data), self._name))

    def query(self, command, size=4096):
        """Write 'command' and return the read response."""

        self.write(command)
        return self.read(size)

    def queryline(self, command):
        """
        Write 'command' and return the read response split per lines, excluding the line break.
        """

        result = self.query(command)
        if result:
            return result.splitlines()[0]
        return ''

USBTMC_IOCTL_INDICATOR_PULSE = 0x5b01
USBTMC_IOCTL_CLEAR = 0x5b02
USBTMC_IOCTL_ABORT_BULK_OUT = 0x5b03
USBTMC_IOCTL_ABORT_BULK_IN = 0x5b04
USBTMC_IOCTL_CLEAR_OUT_HALT = 0x5b06
USBTMC_IOCTL_CLEAR_IN_HALT = 0x5b07

class USBTMC(_Transport):
    """
    Simple implementation of a USBTMC device interface using the Linux kernel USBTMC character
    device driver.
    """

    def __init__(self, devnode='/dev/usbtmc0'):
        """
        The class constructor. The 'devnode' argument is the USBTMC device node to use as a
        transport.
        """

        self._devnode = devnode
        self._fd = None

        super(USBTMC, self).__init__()

        try:
            self._fd = os.open(self._devnode, os.O_RDWR)
        except OSError as err:
            raise Error("error opening device '%s': %s" % (self._devnode, err))

        # Make sure the device is a USBTMC device by invoking a USBTMC-specific IOCTL and checking
        # that it is supported.
        try:
            ioctl(self._fd, USBTMC_IOCTL_CLEAR)
        except IOError as err:
            if err.errno == os.errno.ENOTTY:
                raise Error("'%s' is not a USBTMC device" % self._devnode)

    def __del__(self):
        """The class destructor."""

        if self._fd:
            os.close(self._fd)
            self._fd = None

    def write(self, data):
        """Write command directly to the device."""

        self._dbg("send: %s" % data)
        try:
            os.write(self._fd, data)
        except OSError as err:
            raise Error("error while writing to device '%s': %s" % (self._devnode, err))

    def read(self, size=4096):
        """Read an arbitrary amount of data directly from the device."""

        try:
            data = os.read(self._fd, size)
        except OSError as err:
            raise Error("error while reading from device '%s': %s" % (self._devnode, err))
        self._dbg("received: %s" % data)
        return data

    def ioctl(self, operation):
        """Execute specific IOCTL."""

        try:
            ioctl(self._fd, operation)
        except IOError as err:
            if err.errno == os.errno.ENOTTY:
                raise Error("'%s' is not a USBTMC device" % self._devnode)
            raise Error("ioctl '%#X' for device '%s' failed: %s" % (operation, self._devnode, err))
