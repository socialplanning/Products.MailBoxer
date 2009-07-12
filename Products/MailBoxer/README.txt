MailBoxer - a mailinglist/newsletter/mailarchive-toolbox for ZOPE

 **Please note:** If you plan to upgrade MailBoxer, read the
 CHANGES.txt and UPDATE.txt before installing MailBoxer.

 What is a MailBoxer?

  MailBoxer is a lightweight ZOPE-Product to run mailinglists,
  newsletters and mailarchives. Its main idea is to give you an
  extensible framework for building mailinglist-based applications
  with the power of ZOPE. Out of the box it provides a full featured
  mailinglist/newsletter/mailarchiving-framework.

  Features

   - MailBoxer is easy to use and to configure and can handle
     mime-encoded mails with attachments.

   - People can subscribe/unsubscribe your list by sending an
     "signed" email with a specified email-subject (not body!!!) to
     the same address where the postings will go. No more hazzles
     with passwords and unsubscriptions.

   - You can customize and disable subscription and unsubscription.

   - All mailinglists can be run moderated, members only or public
     available.

   - Mails can be archived (even with attachments) by a combination
     of dates & threads with customizable set of headers.

   - User-friendly archive with powerful search-interface and a
     "one-thread-one-screen"-view with snipped signatures etc.

   - By defining a spamlist, 'dirty' content or misconfigured
     vacation-notifications can be identified and will not be
     forwarded by MailBoxer.

   - MailBoxer can convert all mails to plain-text and strip of
     attachments if you have read enough HTML-Mails and useless
     attachments.

   - MailBoxer provides automatic bounce-detection and a
     management-interface for bounced addresses.

   - MailBoxer implements a sender-loop-limitation, so
     misconfigured vacation-mailser will not kill your server.

   - MailBoxer talks directly to your SMTP-Server. This is very fast
     compared using the standard MailHost.send-method (no more
     overhead for connecting & closing the channel every time you
     send a mail). This is fast enough for even large lists. Optionally
     MailBoxer uses the MaildropHost from Jens Vagelpohl for heavy
     duty-jobs which really needs to be transactional.

   - MailBoxer provides many hooks to integrate it into your own
     Zope-applications.


 What do I have to do to use a MailBoxer?

  Package-Requirements
  
	  MailBoxer requires the
	  "email-package for python":http://sourceforge.net/projects/mimelib.
	  Download and install it (maybe as root) with the same python-binary
	  you use for running your Zope-Server. If you run Zope with Python
	  2.2.3 or higher, the email-package is already included.
	
	  If you want transactional mail-bulking (read-/write-conflicts in the
	  ZODB can result in rare doubled mails, so people will complain about
	  useless traffic etc.pp.), please install the very nice MaildropHost
	  from Jens Vagelpohl (http://www.dataflake.org/software/maildrophost).
	  MaildropHost uses a seperate worker thread to send out the mails only 
	  when the ZODB-transaction was completed successfully. The setup for
	  MaildropHost is easy, please read the README.txt & INSTALL.txt
	  in the MaildropHost-Package.   
	  
	  MailBoxer will use MaildropHost per default when it is installed. 
	  If you upgrade from previous versions of MailBoxer, please be sure to
	  recreate the MailHost-object(s) used by MailBoxer as MaildropHost(s),
	  so MailBoxer can use the transactional features of MaildropHost.
	  
  Setup
      
	  You need python-script-access on a mail-server to work with
	  MailBoxer. This is generally no problem for *nix-users, but maybe one for
	  Windows-users. The following description is *nix-specific.
	
	  If you want to use a MailBoxer, you must first install the gateway-script
	  'smtp2zope.py' as root in a location of the mail-server where your MTA can
	  execute it (Note: In some secured sendmail-installations this could be
	  '/etc/smrsh'). Use the correct python for smtp2zope.py (>=2.1, sometimes an
	  old 1.5 is lurking around as default python). Then you  must add a new alias
	  in the '/etc/aliases' (or '/etc/postfix/aliases' or whatever the name of your
	  MTA-alias-file is) and run 'newaliases'. Your new alias with 'foo' as your
	  mailinglist-email-address-name should look like:
	
	  foo: "|smtp2zope.py http://ZopeServer:Port/PathTo/IdOfMailBoxer/manage_mailboxer [maxBytes]"
	
	  **PLEASE NOTE:**
	
	  The last element of the URL should be '.../manage_mailboxer' if you
	  want to run a mailinglist! This method processes a default workflow
	  for mailinglists, which handles all (un)subscribing and post-processing
	  via the same alias.
	
	  If you only want to use MailBoxer as a mailarchiving-system for
	  your own mails, you can replace '.../manage_mailboxer' with
	  '.../manage_inboxer'. So all mail-traffic will be stored in ZOPE
	  without being processed through a mailinglist.
	
	  If you want to run an open list (everyone can post to the list, but only
	  subscribed members will receive the mail), simply check the
	  unclosed-property of a mailing-list. Another solution is to set up an alias
	  with '.../manage_listboxer',  which forwards all incoming mails to all
	  subscribed members. Please note that in the last case you need an
	  alternate alias for request-handling (subscribe/unsubscribe).
	  You can simply set up something like
	  foo-req: "|smtpzope.py http://.../manage_requestboxer".
	
	  If you want to setup bounce-detection, you have to set an alias
	  pointing to the returnpath of the mailinglist (see below):
	  returnpath: "|smtpzope.py http://.../manage_bounceboxer".
	
	  'maxBytes' is the maximum size of the mail which will be forwarded to ZOPE.
	  **'maxBytes' is optional, but highly recommended!**
	
	  After adding a MailBoxer (see below) you can send all your messages to
	  'foo@yourMailHost.yourDomain'.
	
	  For example: To subscribe to the list send a mail with the subject (not the
	  body) 'subscribe' (without quotes!) to 'foo@yourMailHost.yourDomain'.
	
	
	 Here is a configuration example
	
	  testlist: "|smtp2zope.py http://127.0.0.1:8080/discussions/testlist/manage_mailboxer 20000"
	
	  => Listname 'testlist@...', Id of MailBoxer = 'testlist', only mails with
	     less than 20000 bytes will be submitted to ZOPE (see smtp2zope.py).
	
	  mjablonski: "|smtp2zope.py http://www.zfl.uni-bielefeld.de:8888/mjablonski/mailbox/manage_inboxer"
	
	  => This is an example for storing my personal mail within ZOPE. Id of
	     MailBoxer = 'mailbox'
	
	  secured: "|smtp2zope.py http://user:passwd@localhost:8080/secured/manage_mailboxer"
	
	  => Use something like this if you want to create a protected MailBoxer.
	  Please check Security-Tab of MailBoxer and disable "View"-Permission for
	  Anonymous. You can also set the authorization in smtp2zope.py directly.

 How do I add a MailBoxer?

  You need the "Add MailHosts"-Permission in order to add a MailBoxer:

  - ID (required): The id of your MailBoxer should be 'foo', but can something
    else as well (see above).

  - TITLE (required): The title of your MailBoxer will be used as the
    mailinglist-name. Recommended value: something like 'FOO' or something
    completely different if you want to (see above).

  - EMAIL (required): This is the email-address of the list. Something like
    'foo@yourHost.yourDomain'.

  - MODERATOR (required): This is a space-seperated list of
    email-addresses of the list moderators. Only moderators have the
    right to send mails to a moderated list. **Please note:** The
    first moderator in the list is special: she will receive bouncing
    mails if no returnpath is set. If you want to detect bouncing mails,
    you should use an alias like 'admin@yourlist.dom' and forward these
    mails to ".../manage_bounceboxer" for bounce-handling.

  - SMTP-HOST [optional]: This is the IP or Hostname of your outgoing
    SMTP-Server. Ask your sysadmin if you don't know it. After creation of a
    MailBoxer you can change this in the MailHost-object in your
    MailBoxer-folder. If you don't provide an SMTP-HOST, no MailHost will
    be created at all. This is useful if you want to acquire an already
    existing MailHost. Please note: If you use the MaildropHost as MailHost,
    the SMTP-Server is coded in the config.py of MaildropHost in the filesystem
    and can't be set through the web.

  - MTA-HOSTS [optional]: Space seperated IP's of Mail-Transfer-Agent-Hosts
    which are allowed to gateway messages to your ZopeServer. !!! THIS IS A
    SECURITY FEATURE !!! If you leave this list empty, no security check is
    done and every host can submit mails to your list (even with web-requests).
    Open door for spammers! My advice: When you first install MailBoxer, leave
    this list empty. If it works, enter the IP of the MTA-Server where you have
    installed smtp2zope.py (maybe 127.0.0.1 or a real IP).

  - MODERATED LIST [optional]: Check this, if you want to have a moderated
    list. This can be used for newsletters, too: People can subscribe to your
    newletter-list, but only the moderators can send mails to the list.

  - ARCHIVED LIST [optional]: Check the kind of archive you want for this list.


 What means all the DTML in a MailBoxer?

  After your MailBoxer is created, you can enter the MailBoxer-Folder. You will
  find there several DTML-Methods. You can change them for your needs:

  - 'mail_header' are headers for the bulk-mail. Please note: all headers which
     are set in 'mail_header' will overwrite the same headers in the original
     mail. You can use this to "mask" your moderator if you run a moderated
     list: simply set the 'From'-Header to an meaningless alias so no one can
     see and  fake a moderators email-adress. If you add a body-text in
     mail_header, this will be mailed instead of the incoming mail-body. You
     can access the incoming mail-body with <dtml-var body>.

  - 'mail_footer' is a footer which will be added to all mails. Please note:
     The footer is only visible if the incoming mail has no attachments or in
     plainmail-mode. I'll fix this someday, but at the moment it's ok for me...

  - 'mail_subscribe' is sent, when someone subscribes to your list. First a
     mail with a randomized md5-key is sent to the sender to verify his
     existence. The sender has to reply this mail in order to fulfill the
     subscription. After a successful subscription a welcome message is sent.

  - 'mail_unsubscribe' is sent, when someone unsubscribes from your list. First
     a mail with a randomized md5-key is sent to the sender to verify his
     existence. The sender has to reply this mail in order to fulfill the
     unsubscription.

  - 'mail_reply' is sent as an error mail if the sender is unknown.

  - 'mail_moderator' is called, when a message arrives at a moderated-list.
     Please note: Depending on your setup, you need to replace the absolute_url
     with the virtual domain etc.

  - 'mail_search' is a method for searching the mail-archive.

  - 'mail_template' is a template for rendering a mail(thread).

  - 'mail_index' is an DTML-example for viewing the mail-archive.

  - 'mail_approve' is an DTML-example for moderating pending requests.
  
  If you want to use PageTemplates, you can include the archive-DTML's with
  something like:

  <span tal:replace="structure python:here.mail_index(here, request)"></span>


 How can I (re-)configure a MailBoxer?

  You can (re-)configure your MailBoxer with the properties of the
  MailBoxer-Folder.

  **mailto** - Set this to the email-address of your mailinglist. This should
   be something like: 'foo@yourMailHost.yourDomain'

  **maillist** - In 'maillist' all the addresses of the members of the
   mailinglist will be stored. You can also add, delete or modify single
   members by hand. Only the raw-email-address (without the real name) should
   be stored here!!!

  **disabled** - All adresses who exceeded the sender-loop-limitation will
   be put here. They aren't allowed to mail to the list anymore, but will
   still receive the traffic. Useful to prevent misconfigured vacation mailers
   to kill your server.

  **moderator** - Enter email-addresses of list moderators. Only a moderator
   has the right to send emails to the list if 'moderated' is enabled. The
   first moderator receives bouncing mails if no returnpath is set.

  **returnpath** - This will be used as returnpath for bouncing emails.

  **moderated** - If you enable this, only the moderator has the right to send
   mails to all the members of the list. You can use this feature for
   'newsletters' as well.

  **unclosed** - If you check this, everyone (no need to be subscribed)
   is allowed to mail into the list.

  **plainmail** - If you enable this, all mails to the list will be converted
   to plain-text and all attachments will be stripped of. This is very useful,
   if you hate HTML-Mails and all kind of useless attachments..

  **keepdate** - If you enable this, all original mail-dates will be kept for
   the archive. This is only useful if you import existing mail-archives.

  **storage** - A traverseable path to the archive-folder. You can use it
   to rename / localize the "archive" to something like "mailarchive" etc.

  **archived** - If you enable this, all mails to the list will be stored in
   the MailBoxer in date-folder-hierarchies with or without attachemnts.

  **subscribe** - Set this to the 'string' which must be sent to your list as a
   email-subject in order to subscribe to your list. If you leave this blank,
   subscription is disabled. You can use regular expressions for the
   'subscribe' string.

  **unsubscribe** - Set this to the 'string' which must be sent to your list as
   a email-subject in order to unsubscribe. If you leave this blank,
   unsubscription is disabled. It can be a regular expression as well.

  **mtahosts** - Here you can enter a space seperated list of IP's of hosts
   which are allowed to gateway mails to your list. If you leave this empty, no
   security checks will be taken. In order to avoid 'spam over web-requests'
   enter the host-ip of the host where you installed 'smtp2zope.py' for
   minimum.

  **spamlist** - If you want to disclose some addresses from subscribing /
   mailing to your list, put them here. You can use regular expressions as well
   to exclude whole domains etc. You can even give some taboo-words to get rid
   of XXX-advertising-mails and so on.

  **atmask** - This string will replace all @ in your mails when viewing
   mails in the archive.

  **sniplist** - Here you can define regular expressions for snipping mails.

  **catalog** - Traversable path to the Catalog for indexing mails.

  **xmailer** - In order to avoid endless mail-loops, MailBoxer must send an
   unique identifier in the header of the mail. Leave this untouched, if you
   don't know what to do.

  **headers** - If you enter a regular expression, all matching headers will
   be stored in an additional mailHeader-property. For example: If you want
   to store the message-id and the original date of the mail, use something
   like (without quotes): 'message-id|date'. If you want to store all
   headers, use '.*'.

  **batchsize** - MailBoxer transfers usually only one mail to the smtp-server
   for all the recipients. The smtp-server is doing all the work (batchsize = 0).
   If you encounter problems with this configuration (esp. using large lists
   with more than 500 subscribers), you can set batchsize to a positive integer x,
   which means, that MailBoxer will deliver chunks of x mails at once.
   Example: If you set batchsize=50, a mail with 50 recipients is transfered to
   the smtp-server at once, then the next 50 recipients and so on until
   no more recipients are left.

  **senderlimit** - the number of mails a member is allowed to send in
   the time-interval determined by senderinterval.

  **senderinterval** - the number of seconds for the sender-loop-limitation.
   Something like 10 Mails (senderlimit) in 600 seconds (senderinterval)
   is a good starting point (no real person should write more than 10 mails in
   10 minutes, I guess...)

  **hashkey** - This string is used to generate a encrypted key for subscriptions &
   unsubscriptions. Usually there is no need to change it.

  **mailqueue** - traversable path to a storage for queued mails waiting for approvals
    by a moderator.

  **getter** - Hook for application developers (see below). If you enter a
   traversable PythonScript, this will determine the property of the MailBoxers
   dynamically.

  **setter** - Opposite of the getter, see below.

 Some hints for application-developers

  MailBoxer is a subclass of the folder-class. So you can apply all the methods
  for a regular folder, e.g. you can change the properties of your MailBoxer
  with 'manage_changeProperties' through a script. You can use this for
  web-based subscriptions. All mails will be stored as regular folders with
  additional properties (mailDate,  mailFrom, mailSubject). Attachments to
  a mail will be stored as regular file-objects in the mail-folder.

  MailBoxer provides some hooks for application developers. Please have a look
  at the source to understand the MailBoxer-chain-reaction. In short:

   - manage_mailboxer
     This one provides a out-of-the-box-mailinglisten-manager. It handles
     (un)subscriptions and checks if an incoming mail should be forwarded.
     It calls mail_handler, so you can hook into this method with your own
     workflow.

  -  mail_handler
     A DTML-Method with id=mail_handler is called by manage_mailboxer if
     it exists. You can create your own method to process your own workflow.
     This is useful if you want to gateway your MailBoxer to a News-Server.
     Simply send the mail to the alias of the News-Server and then process it
     with listMail(REQUEST).

   - manage_listboxer
     This one stores the mail in the archive and bulks the mail to all members.

   - manage_inboxer
     This one stores the mail in the archive and that's it.

   - manage_requestboxer
     This one handles subscribing/unsubscribing. Useful if you want to
     seperate requests from postings...

   - manage_bounceboxer
     Use this if you want to set up an alias for bounce-handling.

   - getter

     If you set the getter-property (as path) to a PythonScript,
     all properties of the MailBoxer will be retrieved through the
     getter-script. This is useful if you want to use MailBoxer with
     external databases etc. The PythonScript expects an property-id
     as parameter and should return the value for the property or None.
     An example::

       ## Script (Python) "getter-example"
       ##parameters=property
       if property=='maillist':
           return ['one@two.com','two@three.com']

       if property=='moderated':
           return 1

       return None

     If None is returned by the "getter", then the property will be looked
     up in the properties of the MailBoxer. You should use getValueFor of
     a MailBoxer to retrieve the correct automatically determined properties
     in templates etc. Please note: The getter-script is executed with
     'Manager'-Permissions by MailBoxer.

   - setter

     The setter is the opposite of the getter. It is called when a member
     is added or deleted through manage_addMember, manage_delMember and
     when a member is disabled due to the sender-loop-limitation. Have a
     look at the sources to get the idea where the setter is used. Please
     note: The setter-script is executed with 'Manager'-Permissions
     by MailBoxer.

     If None is returned, then the property will be set as default
     MailBoxer-property, otherwise this step will be skipped. You should
     therefore return true (read something) if you have set the property
     in a customized manner.

   - addMailBoxerFolder, addMailBoxerMail, addMailBoxerFile

     If you subclass MailBoxer for CMF / Plone / etc.pp., you should overwrite
     these methods with your own methods which create the correct content-types.


 Known Bugs

  - The mail_footer is only visible for plain-text-mails without attachments.


 Where do I send questions, comments or bug reports?

  Please send all questions regarding MailBoxer to:
  maik.jablonski@uni-bielefeld.de

