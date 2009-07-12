# Copyright (C) 1998-2003 by the Free Software Foundation, Inc.
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

"""Recognizes simple heuristically delimited bounces."""

import re
import email.Iterators

def _c(pattern):
    return re.compile(pattern, re.IGNORECASE)

# This is a list of tuples of the form
#
#     (start cre, end cre, address cre)
#
# where `cre' means compiled regular expression, start is the line just before
# the bouncing address block, end is the line just after the bouncing address
# block, and address cre is the regexp that will recognize the addresses.  It
# must have a group called `addr' which will contain exactly and only the
# address that bounced.
PATTERNS = [
    # sdm.de
    (_c('here is your list of failed recipients'),
     _c('here is your returned mail'),
     _c(r'<(?P<addr>[^>]*)>')),
    # sz-sb.de, corridor.com, nfg.nl
    (_c('the following addresses had'),
     _c('transcript of session follows'),
     _c(r'<(?P<fulladdr>[^>]*)>|\(expanded from: <?(?P<addr>[^>)]*)>?\)')),
    # robanal.demon.co.uk
    (_c('this message was created automatically by mail delivery software'),
     _c('original message follows'),
     _c('rcpt to:\s*<(?P<addr>[^>]*)>')),
    # s1.com (InterScan E-Mail VirusWall NT ???)
    (_c('message from interscan e-mail viruswall nt'),
     _c('end of message'),
     _c('rcpt to:\s*<(?P<addr>[^>]*)>')),
    # Smail
    (_c('failed addresses follow:'),
     _c('message text follows:'),
     _c(r'\s*(?P<addr>\S+@\S+)')),
    # newmail.ru
    (_c('This is the machine generated message from mail service.'),
     _c('--- Below the next line is a copy of the message.'),
     _c('<(?P<addr>[^>]*)>')),
    # turbosport.com runs something called `MDaemon 3.5.2' ???
    (_c('The following addresses did NOT receive a copy of your message:'),
     _c('--- Session Transcript ---'),
     _c('[>]\s*(?P<addr>.*)$')),
    # usa.net
    (_c('Intended recipient:\s*(?P<addr>.*)$'),
     _c('--------RETURNED MAIL FOLLOWS--------'),
     _c('Intended recipient:\s*(?P<addr>.*)$')),
    # hotpop.com
    (_c('Undeliverable Address:\s*(?P<addr>.*)$'),
     _c('Original message attached'),
     _c('Undeliverable Address:\s*(?P<addr>.*)$')),
    # Another demon.co.uk format
    (_c('This message was created automatically by mail delivery'),
     _c('^---- START OF RETURNED MESSAGE ----'),
     _c("addressed to '(?P<addr>[^']*)'")),
    # Next one goes here...
    ]

def process(msg, patterns=None):
    if patterns is None:
        patterns = PATTERNS
    # simple state machine
    #     0 = nothing seen yet
    #     1 = intro seen
    addrs = {}
    state = 0
    for line in email.Iterators.body_line_iterator(msg):
        if state == 0:
            for scre, ecre, acre in patterns:
                if scre.search(line):
                    state = 1
                    break
        if state == 1:
            mo = acre.search(line)
            if mo:
                addr = mo.group('addr')
                if addr:
                    addrs[mo.group('addr')] = 1
            elif ecre.search(line):
                break
    return addrs.keys()
