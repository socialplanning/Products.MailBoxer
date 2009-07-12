#####
###  MailBoxer - a mailinglist/newsletter/mailarchive-framework for ZOPE
##   Copyright (C) 2004 Maik Jablonski (maik.jablonski@uni-bielefeld.de)
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
##   along with this program; if not, write to the Free Software
###  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#####

# Standard library imports
import StringIO, re, difflib, random, md5, time
import cgi, smtplib, rfc822, multifile, mimetools
from email import message_from_string

# Zope 2 imports
from DateTime import DateTime
from Globals import InitializeClass, DTMLFile
from AccessControl import ClassSecurityInfo
from OFS.Folder import Folder
from zLOG import LOG, INFO, PROBLEM, WARNING, ERROR
# XXX This may need to by try/execpt-ified for zopes older than 2.8.x
from persistent.list import PersistentList

# Product imports
import MailBoxerTemplates, MailBoxerTools, Bouncers
from messagevalidators import ValidatorException, setDefaultValidatorChain


# Simple return-Codes for web-callable-methods for the smtp2zope-gate
TRUE = "TRUE"
FALSE = "FALSE"

# mail-parameter in the smtp2http-request
MAIL_PARAMETER_NAME = "Mail"

try:
    import Products.MaildropHost
    MaildropHostIsAvailable = 1
except:
    MaildropHostIsAvailable = 0

try:
    import Products.SecureMailHost
    SecureMailHostIsAvailable = 1
except:
    SecureMailHostIsAvailable = 0

manage_addMailBoxerForm = DTMLFile('dtml/manage_addMailBoxerForm', globals())


def addMailBoxerMailHost(mb, smtphost=''):
    # Add MailHost if a smtphost is given
    if smtphost:
        if MaildropHostIsAvailable:
            mb.manage_addProduct['MaildropHost'].manage_addMaildropHost('MailHost')
            # make MaildropHost transactional
            mb.MailHost.manage_makeChanges(mb.MailHost.title, transactional=1)
        if SecureMailHostIsAvailable:
            mb.manage_addProduct['SecureMailHost'].manage_addMailHost('MailHost',
                                                                      smtp_host=smtphost)
        else:
            mb.manage_addProduct['MailHost'].manage_addMailHost('MailHost',
                                                         smtp_host=smtphost)


def addMailBoxerCatalog(mb):
    # Add ZCatalog
    mb.manage_addProduct['ZCatalog'].manage_addZCatalog('Catalog','Catalog')

    try:
        # Here we try to add ZCTextIndex => 2.6.x

        class Extra:
            """ Just a dummy to build records for the Lexicon.
            """
            pass

        wordSplitter = Extra()
        wordSplitter.group = 'Word Splitter'
        wordSplitter.name = 'Whitespace splitter'

        caseNormalizer = Extra()
        caseNormalizer.group = 'Case Normalizer'
        caseNormalizer.name = 'Case Normalizer'

        mb.Catalog.manage_addProduct['ZCTextIndex'].manage_addLexicon(
                                                    'Lexicon', 'Lexicon',
                                                    (wordSplitter,
                                                     caseNormalizer))

        extra = Extra()
        extra.index_type = 'Okapi BM25 Rank'
        extra.lexicon_id = 'Lexicon'

        mb.Catalog.manage_addIndex('mailDate', 'DateIndex')
        mb.Catalog.addIndex('mailFrom', 'ZCTextIndex', extra)
        mb.Catalog.addIndex('mailSubject', 'ZCTextIndex', extra)
        mb.Catalog.addIndex('mailBody', 'ZCTextIndex', extra)

    except:
        # Old Zope => maybe I remove this sometimes...;)

        mb.Catalog.manage_addIndex('mailDate', 'FieldIndex')
        mb.Catalog.manage_addIndex('mailFrom', 'TextIndex')
        mb.Catalog.manage_addIndex('mailSubject', 'TextIndex')
        mb.Catalog.manage_addIndex('mailBody', 'TextIndex')


def addMailBoxerDTML(mb):
    # Add dtml-templates
    for (id, data) in MailBoxerTemplates.MailBoxerTemplates.items():
        mb.addDTMLMethod(id, file=data)

def setMailBoxerProperties(mb, REQUEST, kw):
    # Set properties of MailBoxer
    apply(mb.manage_changeProperties, (REQUEST,), kw)


def manage_addMailBoxer(self, id, title='', smtphost='',
                                            REQUEST=None, **kw):
    """ Add a new MailBoxer to current ObjectManager. """

    mb = MailBoxer(id, title)
    self._setObject(id,mb)
    mb = self._getOb(id)

    setMailBoxerProperties(mb, REQUEST, kw)
    addMailBoxerMailHost(mb, smtphost)
    # Add archive-folder
    mb.addMailBoxerFolder(mb, 'archive', 'Archive')
    addMailBoxerCatalog(mb)
    addMailBoxerDTML(mb)
    # Setup the default checkMail validator chain
    setDefaultValidatorChain(mb)

    # Redirect if requested TTW
    if REQUEST:
        return self.manage_main(self, REQUEST, update_menu=1)


class MailBoxer(Folder):
    """ Folder with maillist-managing-methods. """

    ###
    # Class-definitions
    ##

    security = ClassSecurityInfo()
    meta_type = 'Mail Boxer'

    manage_options = Folder.manage_options + ({'label': 'Bounce',
                                               'action': 'manage_bounceForm'},)

    archive_options = ['not archived', 'plain text', 'with attachments']

    # init properties in class; very useful when upgrading MailBoxer...
    mailto = ''
    maillist = []
    disabled = []
    moderator = []
    returnpath = ''
    moderated = 0
    unclosed = 0
    plainmail = 0
    keepdate = 0
    storage = 'archive'
    archived = archive_options[0]
    subscribe = 'subscribe'
    unsubscribe = 'unsubscribe'
    mtahosts = []
    spamlist = []
    atmask = '(at)'
    sniplist = [r'(\n>[^>].*)+|(\n>>[^>].*)+',
                r'(?s)\n-- .*',
                r'(?s)\n_+\n.*']
    catalog = 'Catalog'
    xmailer = 'MailBoxer'
    headers = ''
    batchsize = 0
    senderlimit = 10                # default: no more than 10 mails
    senderinterval = 600            # in 10 minutes (= 600 seconds) allowed
    hashkey = str(random.random())
    mailqueue = 'mqueue'
    getter = ''
    setter = ''

    # Internal storages for bounces and sender-loop-limitation
    bounces = {}
    sendercache = {}

    # counter for unique message-ids
    _uid = 0

    # counter for queued mails
    _mid = 0

    _properties = (
        {'id':'title', 'type':'string', 'mode':'w'},
        {'id':'mailto', 'type':'string', 'mode':'wd'},
        {'id':'maillist', 'type':'lines', 'mode':'wd'},
        {'id':'disabled', 'type':'lines', 'mode':'wd'},
        {'id':'moderator', 'type':'lines', 'mode':'wd'},
        {'id':'returnpath','type':'string', 'mode':'wd'},
        {'id':'moderated', 'type':'boolean', 'mode':'wd'},
        {'id':'unclosed','type':'boolean','mode':'wd'},
        {'id':'plainmail', 'type':'boolean', 'mode':'wd'},
        {'id':'keepdate', 'type':'boolean', 'mode':'wd'},
        {'id':'storage', 'type':'string', 'mode':'wd'},
        {'id':'archived', 'type':'selection','mode':'wd',
                      'select_variable':'archive_options'},
        {'id':'subscribe', 'type':'string', 'mode':'wd'},
        {'id':'unsubscribe','type':'string', 'mode':'wd'},
        {'id':'mtahosts', 'type':'tokens', 'mode':'wd'},
        {'id':'spamlist', 'type':'lines', 'mode':'wd'},
        {'id':'atmask', 'type':'string', 'mode':'wd'},
        {'id':'sniplist', 'type':'lines', 'mode':'wd'},
        {'id':'catalog', 'type':'string', 'mode':'wd'},
        {'id':'xmailer', 'type':'string', 'mode':'wd'},
        {'id':'headers', 'type':'string', 'mode':'wd'},
        {'id':'batchsize','type':'int','mode':'wd'},
        {'id':'senderlimit','type':'int','mode':'wd'},
        {'id':'senderinterval','type':'int','mode':'wd'},
        {'id':'hashkey','type':'string','mode':'wd'},
        {'id':'mailqueue','type':'string','mode':'wd'},
        {'id':'getter','type':'string','mode':'wd'},
        {'id':'setter','type':'string','mode':'wd'},
       )


    def __init__(self, id, title):
        """ Initialize a MailBoxer. """

        self.id = id
        self.title = title
        self.hashkey = str(random.random())


    ###
    # Universal getter / setter for retrieving / storing properties
    # or calling appropriate handlers in ZODB
    ##

    security.declareProtected('Manage properties', 'setValueFor')
    def setValueFor(self, key, value):
        # Sets a value for key as property
        # if available, a dynamic setter will be used

        setter = self.getProperty('setter')
        if setter:
            setterHandler = self.unrestrictedTraverse(setter, default=None)
            if setterHandler is not None:
                proxy_roles = setterHandler._proxy_roles
                try:
                    setterHandler._proxy_roles = ('Manager',)
                    result = setterHandler(key, value)
                finally:
                    setterHandler._proxy_roles = proxy_roles

                if result is not None:
                    return

        # Use manage_changeProperties as default for setting properties
        self.manage_changeProperties({key:value})

    security.declareProtected('Access contents information', 'getValueFor')
    def getValueFor(self, key):
        # Returns value for property;
        # if available, a dynamic getter will be used

        getter = self.getProperty('getter')
        if getter:
            getterHandler = self.unrestrictedTraverse(getter, default=None)
            if getterHandler is not None:
                proxy_roles = getterHandler._proxy_roles
                try:
                    getterHandler._proxy_roles = ('Manager',)
                    result = getterHandler(key)
                finally:
                    getterHandler._proxy_roles = proxy_roles

                if result is not None:
                    return result

        # Our stored properties are the default
        return self.getProperty(key)


    ###
    # Factory-methods for creating objects in mail-archive
    # Overwrite, if you subclass MailBoxer
    # for other environments like CMF/Plone
    ##

    security.declareProtected('Add Folders', 'addMailBoxerFolder')
    def addMailBoxerFolder(self, context, id, title):
        """ Adds an archive-folder.

            A MailBoxerFolder should be derived
            from plain-Zope-Folders.
        """

        context.manage_addFolder(id, title=title)

    security.declareProtected('Add Folders', 'addMailBoxerMail')
    def addMailBoxerMail(self, context, id, title):
        """ Adds an container for a Mail.

            MailBoxerMail should be derived
            from plain-Zope-Folder to store properties,
            replies and attachements.
        """

        context.manage_addFolder(id, title=title)

    security.declareProtected('Add Folders', 'setMailBoxerMailProperty')
    def setMailBoxerMailProperty(self, MailBoxerMail, pkey, pvalue, ptype):
        """ Adds / sets a property of MailBoxerFile. """

        MailBoxerMail.manage_addProperty(pkey, pvalue, ptype)


    security.declareProtected('Add Folders', 'catalogMailBoxerMail')
    def catalogMailBoxerMail(self, MailBoxerMail):
        """ Catalogs MailBoxerFile. """

        # Index the new created mailFolder in the catalog
        Catalog = self.unrestrictedTraverse(self.getValueFor('catalog'),
                                            default=None)
        if Catalog is not None:
            Catalog.catalog_object(MailBoxerMail)


    security.declareProtected('Add Documents, Images, and Files',
                                             'addMailBoxerFile')
    def addMailBoxerFile(self, context, id, title, data, content_type):
        """ Adds an attachment as File.

            MailBoxerFile should be derived
            from plain-Zope-File to store title (=>filename),
            data and content-type for an attachemnt.
        """

        context.manage_addFile(id, title=title, file=data,
                               content_type=content_type)

    ###
    # Public methods to be called via smtp2zope-gateway
    ##

    security.declareProtected('View', 'manage_mailboxer')
    def manage_mailboxer(self, REQUEST):
        """ Default for a all-in-one mailinglist-workflow.

            Handles (un)subscription-requests and
            checks for loops etc & bulks mails to list.
        """

        if self.checkMail(REQUEST):
            return FALSE

        # Check for subscription/unsubscription-request
        if self.requestMail(REQUEST):
            return TRUE

        # Process the mail...
        self.processMail(REQUEST)
        return TRUE


    security.declareProtected('View', 'manage_requestboxer')
    def manage_requestboxer(self, REQUEST):
        """ Handles un-/subscribe-requests.

            Check mails for (un)subscription-requests,
            returns (un)subscribed adress if request
            was successful.
        """

        if self.checkMail(REQUEST):
            return FALSE

        # Check for subscription/unsubscription-request
        self.requestMail(REQUEST)
        return TRUE


    security.declareProtected('View', 'manage_listboxer')
    def manage_listboxer(self, REQUEST):
        """ Send a mail to all members of the list.

            Puts a mail into archive and then bulks
            it to all members on list.
        """

        if self.checkMail(REQUEST):
            return FALSE

        self.listMail(REQUEST)
        return TRUE


    security.declareProtected('View', 'manage_inboxer')
    def manage_inboxer(self, REQUEST):
        """ Wrapper to mail directly into archive.

            This is just a wrapper method if you
            want to use MailBoxer as mailarchive-system.
        """

        if self.checkMail(REQUEST):
            return FALSE

        self.manage_addMail(self.getMailFromRequest(REQUEST))
        return TRUE


    security.declareProtected('View', 'manage_bounceboxer')
    def manage_bounceboxer(self, REQUEST):
        """ Check for bounced mails.
        """

        if self.checkMail(REQUEST):
            return FALSE

        bouncedAddresses = self.bounceMail(REQUEST)

        if bouncedAddresses:
            return TRUE
        else:
            return FALSE


    security.declareProtected('View', 'manage_moderateMail')
    def manage_moderateMail(self, REQUEST):
        """ Approves / discards a mail for a moderated list. """

        action = REQUEST.get('action','')
        if (REQUEST.get('pin') == self.pin(self.getValueFor('mailto'))):
            mqueue = self.restrictedTraverse(self.getValueFor('mailqueue'))
            mid = REQUEST.get('mid','-1')

            if not hasattr(mqueue, mid):
                if action in ['approve','discard']:
                    if hasattr(self, "mail_approve"):
                        return self.mail_approve(self, REQUEST, msg="MAIL_NOT_FOUND")
                    else:
                        REQUEST.RESPONSE.setHeader('Content-type','text/plain')
                        return "MAIL NOT FOUND! MAYBE THE MAIL WAS ALREADY PROCESSED."
                else:
                    if hasattr(self, "mail_approve"):
                        return self.mail_approve(self, REQUEST, msg="MAIL_PENDING")
                    else:
                        REQUEST.RESPONSE.setHeader('Content-type','text/plain')
                        if len(mqueue.objectValues()):
                            return "PENDING MAILS IN QUEUE!"
                        else:
                            return "NO PENDING MAILS IN QUEUE!"

            mail = getattr(mqueue, mid).data
            REQUEST.set(MAIL_PARAMETER_NAME, mail)

            # delete queued mail
            mqueue.manage_delObjects([mid])
            if action == 'approve':
                # relay mail to list
                self.listMail(REQUEST)
                if hasattr(self, "mail_approve"):
                    return self.mail_approve(self, REQUEST, msg="MAIL_APPROVE")
                else:
                    REQUEST.RESPONSE.setHeader('Content-type','text/plain')
                    return "MAIL APPROVED\n\n%s" % mail
            else:
                if hasattr(self, "mail_approve"):
                    return self.mail_approve(self, REQUEST, msg="MAIL_DISCARD")
                else:
                    REQUEST.RESPONSE.setHeader('Content-type','text/plain')
                    return "MAIL DISCARDED\n\n%s" % mail

        if hasattr(self, "mail_approve"):
            return self.mail_approve(self, REQUEST, msg="INVALID_REQUEST")
        else:
            REQUEST.RESPONSE.setHeader('Content-type','text/plain')
            return "INVALID REQUEST! Please check your PIN."


    ###
    # Methods for adding members, mails and bounces
    ##

    security.declareProtected('Manage properties','manage_addMember')
    def manage_addMember(self, email):
        """ Add member to maillist. """

        memberlist = list(self.getValueFor('maillist'))

        if email.lower() not in self.lowerList(memberlist):
            memberlist.append(email)
            memberlist.sort()
            self.setValueFor('maillist', memberlist)
            return email


    security.declareProtected('Manage properties','manage_delMember')
    def manage_delMember(self, email):
        """ Deletes member from maillist. """

        memberlist = list(self.getValueFor('maillist'))
        lowerlist = self.lowerList(memberlist)

        if email.lower() in lowerlist:
            index = lowerlist.index(email.lower())
            self.setValueFor('maillist', memberlist[:index] +
                                         memberlist[index+1:])
            return email


    security.declareProtected('Add Folders','manage_addMail')
    def manage_addMail(self, mailString):
        """ Store mail & attachments in traveresed folder archive.

            Returns created folder as object.
        """

        archive = self.restrictedTraverse(self.getValueFor('storage'),
                                          default=None)

        # no archive available? then return immediately
        if archive is None:
            return None

        (header, body) = self.splitMail(mailString)

        # if 'keepdate' is set, get date from mail,
        if self.getValueFor('keepdate'):
            timetuple = rfc822.parsedate_tz(header.get('date'))
            time = DateTime(rfc822.mktime_tz(timetuple))
        # ... take our own date, clients are always lying!
        else:
            time = DateTime()

        # now let's create the date-path (yyyy/yyyy-mm)
        year  = str(time.year())                  # yyyy
        month = "%s-%s" % (year, str(time.mm()))  # yyyy-mm


        # do we have a year folder already?
        if not hasattr(archive, year):
            self.addMailBoxerFolder(archive, year, year)
        yearFolder=getattr(archive, year)

        # do we have a month folder already?
        if not hasattr(yearFolder, month):
            self.addMailBoxerFolder(yearFolder, month, month)
        monthFolder=getattr(yearFolder, month)

        # let's create the mailObject
        mailFolder = monthFolder

        subject = self.mime_decode_header(header.get('subject', 'No Subject'))
        sender = self.mime_decode_header(header.get('from','No From'))
        title = "%s / %s" % (subject, sender)

        # maybe it's a reply ?
        if ':' in subject:
            for currentFolder in monthFolder.objectValues():
                if difflib.get_close_matches(subject,
                                  [currentFolder.getProperty('mailSubject')]):
                    mailFolder=currentFolder

        # search a free id for the mailobject
        id = time.millis()
        while hasattr(mailFolder, str(id)):
             id = id + 1

        id = str(id)

        self.addMailBoxerMail(mailFolder, id, title)
        mailObject = getattr(mailFolder, id)
	
        # unpack & archive attachments
        (TextBody, ContentType, HtmlBody, Attachments) = self.unpackMail(mailString)
        if mailObject and self.getValueFor('archived') == self.archive_options[-1]:
            for file in Attachments:
                id = DateTime().millis()
                # to be sure: test and search for a free id...
                while hasattr(mailObject, str("%s.%s" % (str(id), file['subtype']))):
                    id = id + 1
                self.addMailBoxerFile(mailObject,
                                      "%s.%s" % (str(id), file['subtype']),
                                      file['filename'],
                                      file['filebody'], 
                                      file['maintype'] + '/' + file['subtype'])

        # ContentType is only set for the TextBody
        if ContentType:
            body = TextBody
        else:
            body = self.HtmlToText(HtmlBody)

        # and now add some properties to our new mailobject
        self.setMailBoxerMailProperty(mailObject, 'mailFrom', sender, 'string')
        self.setMailBoxerMailProperty(mailObject, 'mailSubject', subject, 'string')
        self.setMailBoxerMailProperty(mailObject, 'mailDate', time, 'date')
        self.setMailBoxerMailProperty(mailObject, 'mailBody', body, 'text')

        # insert header if a regular expression is set and matches
        headers_regexp = self.getValueFor('headers')
        if headers_regexp:
            msg = mimetools.Message(StringIO.StringIO(mailString))
            headers = []
            for (key, value) in msg.items():
                if re.match(headers_regexp, key, re.IGNORECASE):
                    headers.append('%s: %s' % (key, value.strip()))

            self.setMailBoxerMailProperty(mailObject, 'mailHeader', headers, 'lines')

        self.catalogMailBoxerMail(mailObject)
        return mailObject


    security.declareProtected('Manage properties','manage_bounceForm')
    manage_bounceForm = DTMLFile('dtml/manage_bounceForm', globals())

    security.declareProtected('Manage properties','manage_resetBounces')
    def manage_resetBounces(self, ids, REQUEST=None):
        """ Removes bounced addresses from bounces-list.
        """

        for addr in ids:
            if self.bounces.has_key(addr):
                del(self.bounces[addr])

        self.bounces = self.bounces

        if REQUEST:
            return self.manage_bounceForm(REQUEST, update_menu=1)


    security.declareProtected('Manage properties','manage_deleteBounces')
    def manage_deleteBounces(self, ids, REQUEST=None):
        """ Deletes bounced addresses from maillist. """

        for addr in ids:
            self.manage_delMember(addr)

        self.manage_resetBounces(ids)

        if REQUEST:
            return self.manage_bounceForm(REQUEST, update_menu=1)
    
    
    security.declareProtected('View', 'manage_event')
    def manage_event(self, event_codes, headers):
        """ Handle event conditions passed up from smtp2zope.
        
            Primarily this method will be called by XMLRPC from smtp2zope.
        
        """
        mail_templates = []; mail_template_names = []
        for code in event_codes:
            # look for a default template only if we don't have a handler
            # for one of the event_codes we've been passed
            try:
                template = getattr(self, 'mail_event_%s' % code, self.mail_event_default)
                
            except AttributeError:
                template = None
            
            if template.__name__ not in mail_template_names:
                mail_templates.append(template)
                mail_template_names.append(template.__name__)
            
        for mail_template in mail_templates:
            # the templates is passed _all_ the event codes because
            # if might be using the default template to control the result
            mail_template(self, event_codes=event_codes, headers=headers)
    
            
    ###
    # Little universal helpers for processing a mail through MailBoxer
    ##

    def setCheckMailCallback(self, validator, position=None):
        """Add the validator to the callback chain at the correct position.
        If no position is passed, just append it to the end of the chain.
        """
        chain = getattr(self, '_check_mail_callback_chain', None)
        if chain is None:
            chain = PersistentList()
            self._check_mail_callback_chain = chain
        if position is None:
            chain.append(validator)
        else:
            chain.insert(position, validator)

    def checkMail(self, REQUEST):
        # Run through the list of registered validators.
        message = self.getMailFromRequest(REQUEST)
        message = message_from_string(message)
        validators = getattr(self, '_check_mail_callback_chain', [])
        # XXX/BBB This is probably wrong, but we need to migrate existing instances.
        #         Perhaps we should look for a class variable flag too?
        if validators == []:
            setDefaultValidatorChain(self)
            validators = getattr(self, '_check_mail_callback_chain')
        try:
            for validator in validators:
                validator(message, self, REQUEST)
        except ValidatorException, e:
            return str(e)

    def sendSubscribeRequestFor(self, address, name, pin):
        self.mail_subscribe_request(self,
                                    subscriber_address=address,
                                    subscriber_name=name,
                                    pinvalue=pin)

    def sendSubscribeConfirmationFor(self, address, name=''):
        self.mail_subscribe_welcome(self,
                                    subscriber_address=address,
                                    subscriber_name=name)

    def sendUnsubscribeRequestFor(self, address, name, pin):
        self.mail_unsubscribe_request(self,
                                      subscriber_address=address,
                                      subscriber_name=name,
                                      pinvalue=pin)

    def sendUnsubscribeConfirmationFor(self, address, name):
        self.mail_unsubscribe_confirm(self, 
                                      subscriber_address=address,
                                      subscriber_name=name)

    def sendBounceTo(self, address, name, subject='No Subject'):
        self.mail_bounce_reply(self,
                               address=address,
                               name=name,
                               subject=subject)

    def requestMail(self, REQUEST):
        # Handles un-/subscribe-requests.

        mailString = self.getMailFromRequest(REQUEST)
        (header, body) = self.splitMail(mailString)

        # get subject
        subject = self.mime_decode_header(header.get('subject',''))

        # get email-address
        sender = self.mime_decode_header(header.get('from',''))
        (name, email) = self.parseaddr(sender)

        memberlist = self.lowerList(self.getValueFor('maillist'))

        # subscription? only subscribe if subscription is enabled.
        subscribe = self.getValueFor('subscribe')
        if (subscribe <> '' and
            re.match('(?i)' + subscribe + "|.*: " + subscribe, subject)):

            if email.lower() not in memberlist:
                pin = self.pin(email)
                if subject.find(pin) <> -1:
                    self.manage_addMember(email)
                    self.sendSubscribeConfirmationFor(email, name)
                else:
                    self.sendSubscribeRequestFor(email, name, pin)
            else:
                self.sendBounceTo(email, name, subject)
            return email

        # unsubscription? only unsubscribe if unsubscription is enabled...
        unsubscribe = self.getValueFor('unsubscribe')
        if (unsubscribe <> '' and
            re.match('(?i)' + unsubscribe + "|.*: " + unsubscribe, subject)):
            if email.lower() in memberlist:
                pin = self.pin(email)
                if subject.find(pin) <> -1:
                    self.manage_delMember(email)
                    self.sendUnsubscribeConfirmationFor(email, name)
                else:
                    self.sendUnsubscribeRequestFor(email, name, pin)
            else:
                self.sendBounceTo(email, name, subject)
            return email


    def listMail(self, REQUEST):
        # Send a mail to all members of the list.

        mailString = self.getMailFromRequest(REQUEST)

        # store mail in the archive? get context for the mail...
        context = None
        if self.getValueFor('archived') <> self.archive_options[0]:
            context = self.manage_addMail(mailString)
        if context is None:
            context = self

        (header, body) = self.splitMail(mailString)

        # plainmail-mode? get the plain-text of mail...
        if self.getValueFor('plainmail'):
            (header['content-type'], body) = self.getPlainBodyFromMail(mailString)


        # get custom header & footer
        (customHeader, customBody) = self.splitMail(self.mail_header(context,
                                                    REQUEST,
                                                    getValueFor=self.getValueFor,
                                                    title=self.getValueFor('title'),
                                                    mail=header,
                                                    body=body).strip())

        customFooter = self.mail_footer(context, REQUEST,
                                                 getValueFor=self.getValueFor,
                                                 title=self.getValueFor('title'),
                                                 mail=header,
                                                 body=body).strip()


        # Patch msg-headers with customHeaders
        msg = mimetools.Message(StringIO.StringIO(mailString))

        for hdr in customHeader.keys():
            if customHeader[hdr]:
                msg[hdr.capitalize()]=customHeader[hdr]
            else:
                del msg[hdr]

        newHeader = ''.join(msg.headers)

        # If customBody is not empty, use it as new mailBody
        if customBody.strip():
            body=customBody

        newMail = "%s\r\n%s\r\n%s" % (newHeader, body, customFooter)

        # Get members
        memberlist = self.getValueFor('maillist')

        # Remove "blank" / corrupted / doubled entries
        maillist=[]
        for email in memberlist:
            if '@' in email and email not in maillist:
                maillist.append(email)

        # if no returnpath is set, use first moderator as returnpath
        returnpath=self.getValueFor('returnpath')
        if not returnpath:
            returnpath = self.getValueFor('moderator')[0]

        if ((MaildropHostIsAvailable and
             getattr(self, "MailHost").meta_type=='Maildrop Host')):
            TransactionalMailHost = getattr(self, "MailHost")
            # Deliver each mail on its own with a transactional MailHost
            batchsize = 1
        else:
            TransactionalMailHost = None
            batchsize = self.getValueFor('batchsize')

        # start batching mails
        while maillist:
            # if no batchsize is set (default)
            # or batchsize is greater than maillist,
            # bulk all mails in one batch,
            # otherwise bulk only 'batch'-mails at once
            if (batchsize == 0) or (batchsize > len(maillist)):
                batch = len(maillist)
            else:
                batch = batchsize

            if TransactionalMailHost:
                 TransactionalMailHost._send(returnpath, maillist[0:batch], newMail)
            else:
                smtpserver = smtplib.SMTP(self.MailHost.smtp_host,
                                          int(self.MailHost.smtp_port))
                smtpserver.sendmail(returnpath, maillist[0:batch], newMail)
                smtpserver.quit()

            # remove already bulked addresses
            maillist = maillist[batch:]


    def processMail(self, REQUEST):
        # Checks if member is allowed to send a mail to list

        mailString = self.getMailFromRequest(REQUEST)
        (header, body) = self.splitMail(mailString)

        sender = self.mime_decode_header(header.get('from',''))
        (name, email) = self.parseaddr(sender)

        # lower-case all addresses for comparisons
        email = email.lower()
        
        # Get members
        try:
            memberlist = self.lowerList(self.getValueFor('mailinlist'))
        except:
            memberlist = self.lowerList(self.getValueFor('maillist'))

        # Get moderators
        moderatorlist = self.lowerList(self.getValueFor('moderator'))
        
        moderated = self.getValueFor('moderated')
        unclosed = self.getValueFor('unclosed')

        # message to a moderated list... relay all mails from a moderator
        if moderated and email not in moderatorlist:
            if (email in memberlist) or unclosed:
                mqueue = self.restrictedTraverse(self.getValueFor('mailqueue'),
                                                 default=None)

                # create a default-mailqueue if the traverse to mailqueue fails...
                if mqueue is None:
                    self.setValueFor('mailqueue', 'mqueue')
                    self.addMailBoxerFolder(self, 'mqueue', '')
                    mqueue = self.mqueue

                title = self.mime_decode_header("%s / %s" % (
                                                      header.get('subject','No subject'),
                                                      header.get('from','No sender')))

                # search for new unique id for mail to queue
                oids = mqueue.objectIds()
                self._mid = self._mid + 1
                while(str(self._mid) in oids):
                    self._mid = self._mid + 1
                mid = str(self._mid)
                self.addMailBoxerFile(mqueue, mid, title, mailString, 'text/plain')
                self.mail_moderator(self, REQUEST, mid=mid, mail=header, body=body)
            else:
                self.mail_reply(self, REQUEST, mail=header, body=body)

            return email

        # traffic! relay all mails to a unclosed list or
        # relay if it is sent from members and moderators...

        if unclosed or (email in (memberlist + moderatorlist)):
            if hasattr(self, 'mail_handler'):
                self.mail_handler(self, REQUEST, mail=header, body=body)
            else:
                self.listMail(REQUEST)
            return email

        # if all previous tests fail, it must be an unknown sender.
        self.mail_reply(self, REQUEST, mail=header, body=body)


    def bounceMail(self, REQUEST):
        # Check a mail for bounces

        mailString = self.getMailFromRequest(REQUEST)

        # Mailman-Bounce-detectors can threw wired exceptions for
        # wired mails...
        try:
            bouncedAddresses = Bouncers.ScanMessage(mailString)
        except:
            bouncedAddresses = []

        if bouncedAddresses:
            # Get lowered member-list
            memberlist=self.lowerList(self.getValueFor('maillist'))

            for item in bouncedAddresses:
                if item.lower() in memberlist:
                    # Create an entry for bouncer, if it not exists...
                    if not self.bounces.has_key(item):
                       self.bounces[item]=[0, DateTime(), DateTime()]

                    # Count up and remember last bounce
                    self.bounces[item] = [self.bounces[item][0]+1,
                                          self.bounces[item][1], DateTime()]

                    self.bounces = self.bounces

            message = 'Mail bounced for: %s' % ', '.join(bouncedAddresses)
            LOG('MailBoxer', PROBLEM, message)

        return bouncedAddresses


    def getMailFromRequest(self, REQUEST):
        # returns the Mail from the REQUEST-object as string

        return str(REQUEST[MAIL_PARAMETER_NAME])


    def uniqueMessageId(self):
        # returns a unique message-id

        msgid = '<%s.%s.%s.%s>' % (
            self.getValueFor('xmailer'),
            self._uid,
            time.time(),
            self.getValueFor('mailto'))
        self._uid = self._uid + 1
        return msgid


    def pin(self, addr):
        # returns the hex-digits for a randomized md5 of sender.

        (name, email) = self.parseaddr(addr)
        res = md5.new(email.lower() + self.getValueFor('hashkey')).hexdigest()
        return res[:8]

    ###
    # Some wrappers for generic mail-parse-tools from MailBoxerTools    
    ##
    
    def splitMail(self, mailString):
        # return (header,body) of a mail given as string
        return MailBoxerTools.splitMail(mailString)


    def mime_decode_header(self, header):
        # Returns the unfolded and undecoded header
        return MailBoxerTools.mime_decode_header(header)


    def parseaddr(self, header):
        # wrapper for rfc822.parseaddr, returns (name, addr)
        return MailBoxerTools.parseaddr(header)


    def parseaddrList(self, header):
        # wrapper for rfc822.AddressList, returns list of (name, addr)
        return MailBoxerTools.parseaddrList(header)


    def lowerList(self, stringlist):
        # lowers all items of a list
        return MailBoxerTools.lowerList(stringlist)


    def HtmlToText(self, html):
        # converts html to text
        return MailBoxerTools.convertHTML2Text(html)


    def getPlainBodyFromMail(self, mailString):
        # get content-type and body from mail given as string
        return MailBoxerTools.getPlainBodyFromMail(mailString)


    def unpackMail(self, mailString):
        # returns plainbody, content-type, htmlbody and attachments
        return MailBoxerTools.unpackMail(mailString)


    ###
    # Simple helpers for displaying mails from archive
    ##

    def snipMail(self, strg):
        # snips all regexps from strg and urlifies it

        for regexp in self.getValueFor('sniplist'):
            if regexp:
                strg = re.sub(regexp,'[...]',strg)

        strg = cgi.escape(strg)

        # Urlifing can be done better... but it's quite good
        strg = re.sub(r'(?P<url>http[s]?://[-_&;,?:~=%#+/.0-9a-zA-Z]+)',
                      r'<a href="\g<url>">\g<url></a>', strg)

        return strg.strip()


    def at(self, strg):
        # replaces all @ with the atmask

        return(strg.replace('@', self.getValueFor('atmask')))


    def textwrap(self, text, width):
        # Wraps text to width

        return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line[line.rfind('\n')+1:])
                         + len(word.split('\n',1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )


    def searchMailBoxerArchive(self, query):
        # Searches the archive and remove replies from result-set

        result=[]
        threads=[]

        Catalog = self.restrictedTraverse(self.getValueFor('catalog'),
                                                               default=None)
        query = (Catalog.searchResults(mailFrom=query)+
                 Catalog.searchResults(mailSubject=query)+
                 Catalog.searchResults(mailBody=query))

        for brain in query:
            obj = brain.getObject()
            thread = obj
            if obj.aq_parent.hasProperty('mailDate'):
                thread = obj.aq_parent
            if thread not in threads:
                result.append(obj)
                threads.append(thread)

        return result


    def archiveFolders(self, context):
        # Gets all folderish objects from the archive

        archive = self.restrictedTraverse(self.getValueFor('storage'))
        if context==self:
            return [archive]

        result = []
        for item in context.objectValues():
            if item.isPrincipiaFolderish and item not in [archive, self]:
                result.append(item)
        return result


    def nextObject(self, context):
        # Returns next Folder in context or None

        archive = self.restrictedTraverse(self.getValueFor('storage'))
        if archive is None or context in [self, archive]:
            return None

        parentObjectValues = self.archiveFolders(context.aq_parent)
        parentObjectIds = [folder.getId() for folder in parentObjectValues]
        parentObjectIds.sort()

        if context.getId() in parentObjectIds:
            parentPosition = parentObjectIds.index(context.getId())

            if parentPosition+1<len(parentObjectIds):
                return getattr(context,str(parentObjectIds[parentPosition+1]))

            elif context<>self and context.aq_parent<>self:
                if self.nextObject(context.aq_parent):
                    objList = self.archiveFolders(self.nextObject(
                                                             context.aq_parent))
                    if objList:
                        return objList[0]

        return None


    def previousObject(self, context):
        # Return previous Folder in context or None

        archive = self.restrictedTraverse(self.getValueFor('storage'))
        if archive is None or context in [self, archive]:
            return None

        parentObjectValues = self.archiveFolders(context.aq_parent)
        parentObjectIds = [folder.getId() for folder in parentObjectValues]
        parentObjectIds.sort()

        if context.getId() in parentObjectIds:
            parentPosition = parentObjectIds.index(context.getId())

            if parentPosition > 0:
                return getattr(context,str(parentObjectIds[parentPosition-1]))

            elif context<>self and context.aq_parent<>self:
                if self.previousObject(context.aq_parent):
                    objList = self.archiveFolders(self.previousObject(
                                                             context.aq_parent))
                    if objList:
                        return objList[-1]

        return None


# And here we go to the moon... Houston, we have a problem...
InitializeClass(MailBoxer)
