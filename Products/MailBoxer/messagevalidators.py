# Zope 3 imports
from zope.interface import implements

# Zope 2 imports
from DateTime import DateTime
from zLOG import LOG, INFO, PROBLEM, WARNING, ERROR

# Product imports
from interfaces import IMessageValidator

# Standard library imports
import rfc822
import re


class ValidatorException(Exception):
    pass


class BaseValidator:
    implements(IMessageValidator)


class RemoteIPValidator(BaseValidator):
    """Check for correct IP
    """

    def __call__(self, message, mailboxer, REQUEST):
        mtahosts = mailboxer.getValueFor('mtahosts')
        if mtahosts:
            if 'HTTP_X_FORWARDED_FOR' in REQUEST.environ.keys():
                REMOTE_IP = REQUEST.environ['HTTP_X_FORWARDED_FOR']
            else:
                REMOTE_IP = REQUEST.environ['REMOTE_ADDR']

            if REMOTE_IP not in mtahosts:
                logmessage = 'Host %s is not allowed' % (REMOTE_IP)
                LOG('MailBoxer', PROBLEM,  logmessage)
                #return logmessage
                raise ValidatorException(logmessage)


class XMailerLoopValidator(BaseValidator):
    """Check for x-mailer-loop
    """

    def __call__(self, message, mailboxer, REQUEST):
        mailString = message.as_string()
        (header, body) = mailboxer.splitMail(mailString)
        if header.get('x-mailer') == mailboxer.getValueFor('xmailer'):
            logmessage = 'Mail already processed'
            LOG('MailBoxer', PROBLEM, logmessage)
            #return logmessage
            raise ValidatorException(logmessage)
        # Check for empty return-path => automatic mail
        if header.get('return-path', '') == '<>':
            mailboxer.bounceMail(REQUEST)
            logmessage = 'Automated response detected from %s'
            LOG('MailBoxer', PROBLEM, logmessage % (header.get('from', '<>')))
            #return (message)
            raise ValidatorException(logmessage)
        # Check for hosed denial-of-service-vacation mailers
        # or other infinite mail-loops...
        sender = mailboxer.mime_decode_header(header.get('from', 'No Sender'))
        (name, email) = rfc822.parseaddr(sender)
        email = email.lower()
        disabled = list(mailboxer.getValueFor('disabled'))
        if email in disabled:
            logmessage = '%s is disabled.' % sender
            LOG('MailBoxer', PROBLEM, logmessage)
            #return logmessage
            raise ValidatorException(logmessage)
        senderlimit = mailboxer.getValueFor('senderlimit')
        senderinterval = mailboxer.getValueFor('senderinterval')
        if senderlimit and senderinterval:
            sendercache = mailboxer.sendercache
            ntime = int(DateTime())
            if sendercache.has_key(email):
                sendercache[email].insert(0, ntime)
            else:
                sendercache[email] = [ntime]
            etime = ntime-senderinterval
            count = 0
            for atime in sendercache[email]:
                if atime > etime:
                    count += 1
                else:
                    break
            # prune our cache back to the time intervall
            sendercache[email] = sendercache[email][:count]
            mailboxer.sendercache = sendercache
            if count > senderlimit:
                if email not in disabled:
                    mailboxer.setValueFor('disabled', disabled + [email])
                logmessage = ('Sender %s has sent %s mails in %s seconds' %
                                              (sender, count, senderinterval))
                LOG('MailBoxer', PROBLEM, logmessage)
                #return logmessage
                raise ValidatorException(logmessage)


class SpamValidator(BaseValidator):
    """Check for spam.
    """

    def __call__(self, message, mailboxer, REQUEST):
        mailString = message.as_string()
        for regexp in mailboxer.getValueFor('spamlist'):
            if regexp and re.search(regexp, mailString):
                logmessage = 'Spam detected: %s\n\n%s\n' % (regexp, mailString)
                LOG('MailBoxer', PROBLEM, logmessage)
                #return logmessage
                raise ValidatorException(logmessage)


def setDefaultValidatorChain(mailboxer):
    validators = [RemoteIPValidator(), XMailerLoopValidator(), SpamValidator()]
    for validator in validators:
        mailboxer.setCheckMailCallback(validator)

