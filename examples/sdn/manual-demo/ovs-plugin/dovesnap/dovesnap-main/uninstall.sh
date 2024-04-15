#!/bin/sh

echo uninstalling dovesnap

if [ ! -f /etc/systemd/system/dovesnap.service ] ; then
	echo dovesnap service not installed.
	exit 1
fi

dovesnapid=$(id dovesnap)
if [ "$dovesnapid" = "" ] ; then
	echo no dovesnap user.
	exit 1
fi

sudo service dovesnap stop || true
sudo systemctl disable dovesnap
sudo rm -f /etc/systemd/system/dovesnap.service
sudo userdel -r dovesnap

echo dovesnap uninstalled
