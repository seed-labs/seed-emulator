# Mail Server POC (Not ready)

This is the mail server basic example. It is just on the POC step at this point. 
## Useful resources about setting sendmail
https://rimuhosting.com/support/settingupemail.jsp?mta=sendmail&t=catchall#catchall 
https://blog.edmdesigner.com/send-email-from-linux-command-line/ 
https://kenfavors.com/code/how-to-install-and-configure-sendmail-on-ubuntu/ 
https://www.cier.tech/blog/tech-tutorials-4/post/how-to-install-and-configure-sendmail-on-ubuntu-35 

## What things we can do with this example
1. Run 1 mail server on the mini internet emultor.
2. Receive mail remotely using mutt as a mailclient. Mutt uses IMAP to get mails from the mail server
3. Send mail remotely using telnet 

## What things need to be improved and implemented
1. When configurating the mail server, dns resolv.conf should be set prior to sendmailconfig command. At this point when we render and compile it, sendmailconfig config runs before the setting of the resolv.conf, which leads to hostname error.

2. Can't send mail using mutt because of the tls regarding error. Implementing ssl on sendmail server might solve this problem. Need to improve it or find another way to send mail.

3. postfix is also a wellknown smtp server. If we keep having trouble with sendmail, we can try postfix in the future.

4. Load multiple email server on different hostname (i.e. seedmail.edu and wonmail.com) and make it possible to send and receive mails each other.

## Step 1: load mini-internet-with-dns as a base layer


To get this bin file, you have to run B00-mini-internet, B01-dns-component, and B02-mini-internet-with-dns. 
```python
emu.load('../../B02-mini-internet-with-dns/base_with_dns.bin')
```

## Step 2: Setting Mailserver
We will use a sendmail software to implement SMTP server and a dovecot software to implement IMAP.

```python
web.addSoftware('sendmail dovecot-imapd dovecot-pop3d')
web.appendStartCommand('hostname seedmail.edu')
web.setFile('/etc/mail/sendmail.mc', MailServerFileTemplates['sendmail_mc'])
web.appendStartCommand('m4 /etc/mail/sendmail.mc > /etc/mail/sendmail.cf')
web.appendStartCommand('echo "listen = 0.0.0.0, ::" >> /etc/dovecot/dovecot.conf')
web.setFile('/etc/dovecot/conf.d/10-auth.conf', MailServerFileTemplates['dovecot_auth_conf'])
web.setFile('/etc/dovecot/conf.d/10-mail.conf.add', MailServerFileTemplates['dovecot_mail'])
web.appendStartCommand('cat /etc/dovecot/conf.d/10-mail.conf.add >> /etc/dovecot/conf.d/10-mail.conf')
web.appendStartCommand('echo "y" | sendmailconfig')
web.appendStartCommand('/etc/init.d/sendmail restart')
web.appendStartCommand('/etc/init.d/dovecot restart')
```
## Step3. Setting DNS

Add Nameserver node for mail host and add a record.

```python
dns = emu.getLayer("DomainNameService")
asn_162.createHost('host_2').joinNetwork('net0','10.162.0.72')
dns.install('ns-seedmail-edu').addZone('seedmail.edu.')
dns.getZone('seedmail.edu.').addRecord('mail.seedmail.edu. A 10.162.0.75').addRecord("@ MX 10 mail.seedmail.edu.")
emu.addBinding(Binding('ns-seedmail-edu', filter=Filter(asn=162, ip="10.162.0.72")))
emu.getVirtualNode('ns-seedmail-edu').setDisplayName('seedmail.edu')
```
