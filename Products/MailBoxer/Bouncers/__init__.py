##
# Please note:
#
# All code for Bouncers is taken with permission of Barry A. Warsaw 
# nearly unmodified from GNU Mailman: 
#
# http://www.gnu.org/software/mailman
#
# Thank you, Barry!
##

# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Contains all the common functionality for msg bounce scanning API.

This module can also be used as the basis for a bounce detection testing
framework.  When run as a script, it expects two arguments, the listname and
the filename containing the bounce message.

"""

import sys, email


# If a bounce detector returns Stop, that means to just discard the message.
# An example is warning messages for temporary delivery problems.  These
# shouldn't trigger a bounce notification, but we also don't want to send them
# on to the list administrator.
class _Stop:
    pass
Stop = _Stop()


BOUNCE_PIPELINE = [
    'DSN',
    'Qmail',
    'Postfix',
    'Yahoo',
    'Caiwireless',
    'Exchange',
    'Exim',
    'Netscape',
    'Compuserve',
    'Microsoft',
    'GroupWise',
    'SMTP32',
    'SimpleMatch',
    'SimpleWarning',
    'Yale',
    'LLNL',
    'Sina',
    ]

# msg must be a mimetools.Message
def ScanMessage(mailmsg):

    msg = email.message_from_string(mailmsg)

    for module in BOUNCE_PIPELINE:
        modname = 'Products.MailBoxer.Bouncers.'+module
        __import__(modname)
        addrs = sys.modules[modname].process(msg)
        if addrs is Stop:
            # One of the detectors recognized the bounce, but there were no
            # addresses to extract.  Return one empty element list.
            return ['']
        elif addrs:
            return addrs
    return []
