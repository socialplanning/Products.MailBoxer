# Zope 3 imports
from zope.interface import Interface


class IMessageValidator(Interface):

    def __call__(message, mailinglist, REQUEST):
        """Validates based on information from the email.Message.Message
        instance, the mailing list (which is assumed to be a mailboxer
        instance for now, but which should ultimately just be an interface
        requirement), and the REQUEST.
        """
