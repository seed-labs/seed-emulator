#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random
import os

MailServerFileTemplates: Dict[str, str] = {}

MailServerFileTemplates['mutt_rc'] = '''\

set from = "test@seedmail.edu"
set smtp_url="smtp://test@seedmail.edu:25"
set spoolfile="imap://test@seedmail.edu/INBOX"
set folder="imap://test@seedmail.edu"
set imap_authenticators="plain"

'''

MailServerFileTemplates['sendmail_mc'] = '''\
divert(-1)dnl
#-----------------------------------------------------------------------------
# $Sendmail: debproto.mc,v 8.15.2 2020-03-08 00:39:49 cowboy Exp $
#
# Copyright (c) 1998-2010 Richard Nelson.  All Rights Reserved.
#
# cf/debian/sendmail.mc.  Generated from sendmail.mc.in by configure.
#
# sendmail.mc prototype config file for building Sendmail 8.15.2
#
# Note: the .in file supports 8.7.6 - 9.0.0, but the generated
#	file is customized to the version noted above.
#
# This file is used to configure Sendmail for use with Debian systems.
#
# If you modify this file, you will have to regenerate /etc/mail/sendmail.cf
# by running this file through the m4 preprocessor via one of the following:
#	* make   (or make -C /etc/mail)
#	* sendmailconfig
#	* m4 /etc/mail/sendmail.mc > /etc/mail/sendmail.cf
# The first two options are preferred as they will also update other files
# that depend upon the contents of this file.
#
# The best documentation for this .mc file is:
# /usr/share/doc/sendmail-doc/cf.README.gz
#
#-----------------------------------------------------------------------------
divert(0)dnl
#
#   Copyright (c) 1998-2005 Richard Nelson.  All Rights Reserved.
#
#  This file is used to configure Sendmail for use with Debian systems.
#
define(`_USE_ETC_MAIL_')dnl
include(`/usr/share/sendmail/cf/m4/cf.m4')dnl
VERSIONID(`$Id: sendmail.mc, v 8.15.2-18 2020-03-08 00:39:49 cowboy Exp $')
OSTYPE(`debian')dnl
DOMAIN(`debian-mta')dnl
dnl # Items controlled by /etc/mail/sendmail.conf - DO NOT TOUCH HERE
undefine(`confHOST_STATUS_DIRECTORY')dnl        #DAEMON_HOSTSTATS=
dnl # Items controlled by /etc/mail/sendmail.conf - DO NOT TOUCH HERE
dnl #
dnl # General defines
dnl #
dnl # SAFE_FILE_ENV: [undefined] If set, sendmail will do a chroot()
dnl #	into this directory before writing files.
dnl #	If *all* your user accounts are under /home then use that
dnl #	instead - it will prevent any writes outside of /home !
dnl #   define(`confSAFE_FILE_ENV',             `')dnl
dnl #
dnl # Daemon options - restrict to servicing LOCALHOST ONLY !!!
dnl # Remove `, Addr=' clauses to receive from any interface
dnl # If you want to support IPv6, switch the commented/uncommentd lines
dnl #
FEATURE(`no_default_msa')dnl
dnl DAEMON_OPTIONS(`Family=inet6, Name=MTA-v6, Port=smtp, Addr=::1')dnl
DAEMON_OPTIONS(`Family=inet,  Name=MTA-v4, Port=smtp, Addr=0.0.0.0')dnl
dnl DAEMON_OPTIONS(`Family=inet6, Name=MSP-v6, Port=submission, M=Ea, Addr=::1')dnl
DAEMON_OPTIONS(`Family=inet,  Name=MSP-v4, Port=submission, M=Ea, Addr=0.0.0.0')dnl
dnl #
dnl # Be somewhat anal in what we allow
define(`confPRIVACY_FLAGS',dnl
`needmailhelo,needexpnhelo,needvrfyhelo,restrictqrun,restrictexpand,nobodyreturn,authwarnings')dnl
dnl #
dnl # Define connection throttling and window length
define(`confCONNECTION_RATE_THROTTLE', `15')dnl
define(`confCONNECTION_RATE_WINDOW_SIZE',`10m')dnl
dnl #
dnl # Features
dnl #
dnl # use /etc/mail/local-host-names
FEATURE(`use_cw_file')dnl
dnl #
dnl # The access db is the basis for most of sendmail's checking
FEATURE(`access_db', , `skip')dnl
dnl #
dnl # The greet_pause feature stops some automail bots - but check the
dnl # provided access db for details on excluding localhosts...
FEATURE(`greet_pause', `1000')dnl 1 seconds
dnl #
dnl # Delay_checks allows sender<->recipient checking
FEATURE(`delay_checks', `friend', `n')dnl
dnl #
dnl # If we get too many bad recipients, slow things down...
define(`confBAD_RCPT_THROTTLE',`3')dnl
dnl #
dnl # Stop connections that overflow our concurrent and time connection rates
FEATURE(`conncontrol', `nodelay', `terminate')dnl
FEATURE(`ratecontrol', `nodelay', `terminate')dnl
dnl #
dnl # If you're on a dialup link, you should enable this - so sendmail
dnl # will not bring up the link (it will queue mail for later)
dnl define(`confCON_EXPENSIVE',`True')dnl
dnl #
dnl # Dialup/LAN connection overrides
dnl #
include(`/etc/mail/m4/dialup.m4')dnl
include(`/etc/mail/m4/provider.m4')dnl
dnl #
dnl # Default Mailer setup
MAILER_DEFINITIONS
MAILER(`local')dnl
MAILER(`smtp')dnl
'''

MailServerFileTemplates['dovecot_auth_conf'] = '''\
##
## Authentication processes
##

# Disable LOGIN command and all other plaintext authentications unless
# SSL/TLS is used (LOGINDISABLED capability). Note that if the remote IP
# matches the local IP (ie. you're connecting from the same computer), the
# connection is considered secure and plaintext authentication is allowed.
# See also ssl=required setting.
disable_plaintext_auth = no

# Authentication cache size (e.g. 10M). 0 means it's disabled. Note that
# bsdauth, PAM and vpopmail require cache_key to be set for caching to be used.
#auth_cache_size = 0
# Time to live for cached data. After TTL expires the cached record is no
# longer used, *except* if the main database lookup returns internal failure.
# We also try to handle password changes automatically: If user's previous
# authentication was successful, but this one wasn't, the cache isn't used.
# For now this works only with plaintext authentication.
#auth_cache_ttl = 1 hour
# TTL for negative hits (user not found, password mismatch).
# 0 disables caching them completely.
#auth_cache_negative_ttl = 1 hour

# Space separated list of realms for SASL authentication mechanisms that need
# them. You can leave it empty if you don't want to support multiple realms.
# Many clients simply use the first one listed here, so keep the default realm
# first.
#auth_realms =

# Default realm/domain to use if none was specified. This is used for both
# SASL realms and appending @domain to username in plaintext logins.
#auth_default_realm = 

# List of allowed characters in username. If the user-given username contains
# a character not listed in here, the login automatically fails. This is just
# an extra check to make sure user can't exploit any potential quote escaping
# vulnerabilities with SQL/LDAP databases. If you want to allow all characters,
# set this value to empty.
#auth_username_chars = abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890.-_@

# Username character translations before it's looked up from databases. The
# value contains series of from -> to characters. For example "#@/@" means
# that '#' and '/' characters are translated to '@'.
#auth_username_translation =

# Username formatting before it's looked up from databases. You can use
# the standard variables here, eg. %Lu would lowercase the username, %n would
# drop away the domain if it was given, or "%n-AT-%d" would change the '@' into
# "-AT-". This translation is done after auth_username_translation changes.
#auth_username_format = %Lu

# If you want to allow master users to log in by specifying the master
# username within the normal username string (ie. not using SASL mechanism's
# support for it), you can specify the separator character here. The format
# is then <username><separator><master username>. UW-IMAP uses "*" as the
# separator, so that could be a good choice.
#auth_master_user_separator =

# Username to use for users logging in with ANONYMOUS SASL mechanism
#auth_anonymous_username = anonymous

# Maximum number of dovecot-auth worker processes. They're used to execute
# blocking passdb and userdb queries (eg. MySQL and PAM). They're
# automatically created and destroyed as needed.
#auth_worker_max_count = 30

# Host name to use in GSSAPI principal names. The default is to use the
# name returned by gethostname(). Use "$ALL" (with quotes) to allow all keytab
# entries.
#auth_gssapi_hostname =

# Kerberos keytab to use for the GSSAPI mechanism. Will use the system
# default (usually /etc/krb5.keytab) if not specified. You may need to change
# the auth service to run as root to be able to read this file.
#auth_krb5_keytab = 

# Do NTLM and GSS-SPNEGO authentication using Samba's winbind daemon and
# ntlm_auth helper. <doc/wiki/Authentication/Mechanisms/Winbind.txt>
#auth_use_winbind = no

# Path for Samba's ntlm_auth helper binary.
#auth_winbind_helper_path = /usr/bin/ntlm_auth

# Time to delay before replying to failed authentications.
#auth_failure_delay = 2 secs

# Require a valid SSL client certificate or the authentication fails.
#auth_ssl_require_client_cert = no

# Take the username from client's SSL certificate, using 
# X509_NAME_get_text_by_NID() which returns the subject's DN's
# CommonName. 
#auth_ssl_username_from_cert = no

# Space separated list of wanted authentication mechanisms:
#   plain login digest-md5 cram-md5 ntlm rpa apop anonymous gssapi otp skey
#   gss-spnego
# NOTE: See also disable_plaintext_auth setting.
auth_mechanisms = plain login

##
## Password and user databases
##

#
# Password database is used to verify user's password (and nothing more).
# You can have multiple passdbs and userdbs. This is useful if you want to
# allow both system users (/etc/passwd) and virtual users to login without
# duplicating the system users into virtual database.
#
# <doc/wiki/PasswordDatabase.txt>
#
# User database specifies where mails are located and what user/group IDs
# own them. For single-UID configuration use "static" userdb.
#
# <doc/wiki/UserDatabase.txt>

#!include auth-deny.conf.ext
#!include auth-master.conf.ext

!include auth-system.conf.ext
#!include auth-sql.conf.ext
#!include auth-ldap.conf.ext
#!include auth-passwdfile.conf.ext
#!include auth-checkpassword.conf.ext
#!include auth-vpopmail.conf.ext
#!include auth-static.conf.ext
'''

MailServerFileTemplates['dovecot_mail'] = '''\
mail_location = mbox:~/mail:INBOX=/var/mail/%u
mail_access_groups = mail
lock_method = fcntl
'''

emu = Emulator()

# Load the base layer from the mini-internet-with-dns example
emu.load('../../B02-mini-internet-with-dns/base_with_dns.bin')

base = emu.getLayer("Base")
##########################################1. Setting MailServer###############################################
# 
# 1) Get as_162_webservice_0 node from the existing emu. 
asn_162 = base.getAutonomousSystem(162)
web = asn_162.getHost('webservice_0')

# 2) Set the server ip to static : 10.162.0.75 and displayname
web.updateNetwork('net0', address='10.162.0.75')
web.setDisplayName('seedmail_server')

# 3) Install the needed software : sendmail, dovecot
web.addSoftware('sendmail dovecot-imapd dovecot-pop3d')

# 4) Set configuration files to run sendmail(for smpt) and dovecote(for imap)
web.appendStartCommand('hostname seedmail.edu')
web.setFile('/etc/mail/sendmail.mc', MailServerFileTemplates['sendmail_mc'])
web.appendStartCommand('m4 /etc/mail/sendmail.mc > /etc/mail/sendmail.cf')
web.appendStartCommand('echo "listen = 0.0.0.0, ::" >> /etc/dovecot/dovecot.conf')
web.setFile('/etc/dovecot/conf.d/10-auth.conf', MailServerFileTemplates['dovecot_auth_conf'])
web.setFile('/etc/dovecot/conf.d/10-mail.conf.add', MailServerFileTemplates['dovecot_mail'])
web.appendStartCommand('cat /etc/dovecot/conf.d/10-mail.conf.add >> /etc/dovecot/conf.d/10-mail.conf')

# 5) Add user account test
web.appendStartCommand('useradd -m -g mail test && (echo "test:test" | chpasswd)')

# **** We have a small issue at this point. when applying the sendmail configuration, nameserver is not set (on resolv.cof) it returns error. 
# **** So we need to run "sendmailconfig" command manually when the dockers up.
web.appendStartCommand('echo "y" | sendmailconfig')

# 6) Start service
web.appendStartCommand('/etc/init.d/sendmail restart')
web.appendStartCommand('/etc/init.d/dovecot restart')
##############################################################################################################

####################### 2. Setting Nameserver for the mail server and ADD DNS Record #########################
dns = emu.getLayer("DomainNameService")
asn_162.createHost('host_2').joinNetwork('net0','10.162.0.72')
dns.install('ns-seedmail-edu').addZone('seedmail.edu.')
dns.getZone('seedmail.edu.').addRecord('@ A 10.162.0.75').addRecord('mail.seedmail.edu. A 10.162.0.75').addRecord("@ MX 10 mail.seedmail.edu.")
emu.addBinding(Binding('ns-seedmail-edu', filter=Filter(asn=162, ip="10.162.0.72")))
emu.getVirtualNode('ns-seedmail-edu').setDisplayName('seedmail.edu')
##############################################################################################################

##########################################3. Setting MailClient###############################################

asn_150 = base.getAutonomousSystem(150)
web_150 = asn_150.getHost('webservice_0')
web_150.updateNetwork('net0', address='10.150.0.75')
# We are using mutt as a mail client at this point. 
web_150.addSoftware('mutt')
web_150.setFile('/root/.muttrc', MailServerFileTemplates['mutt_rc'])
web_150.setDisplayName('mail_client')
##############################################################################################################


emu.render()

docker = Docker()
docker.addImage(DockerImage('handsonsecurity/seed-ubuntu:large', [], local=False))
docker.forceImage('handsonsecurity/seed-ubuntu:large')

emu.compile(docker, './output')
