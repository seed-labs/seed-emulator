#!/bin/sh

echo installing dovesnap

giturl=$1

for dep in docker git ; do
	depv=$($dep --version 2>/dev/null)
	if [ "$depv" = "" ] ; then
		echo $dep not installed.
		exit 1
	fi
done

if [ -f /etc/systemd/system/dovesnap.service ] ; then
	echo dovesnap service already installed.
	exit 1
fi

dovesnapid=$(id dovesnap 2>/dev/null)
if [ "$dovesnapid" != "" ] ; then
	echo dovesnap user already exists.
	exit 1
fi

sudo useradd -m dovesnap -G docker
if [ "$giturl" = "" ] ; then
	sudo -u dovesnap -s eval 'cd ~dovesnap && git clone https://github.com/iqtlabs/dovesnap && cd ~dovesnap/dovesnap && git fetch --all --tags && git checkout $(git describe --tags --abbrev=0)' || exit
else
	sudo -u dovesnap -s eval "cd ~dovesnap && git clone $giturl" || exit
fi
sudo -u dovesnap -s eval 'cp ~dovesnap/dovesnap/service.env ~dovesnap' || exit
sudo cp ~dovesnap/dovesnap/dovesnap.service /etc/systemd/system || exit
sudo systemctl daemon-reload || exit
sudo systemctl enable dovesnap || exit
sudo systemctl start dovesnap

echo dovesnap installed
