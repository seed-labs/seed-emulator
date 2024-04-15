#!/bin/sh
set -e

echo running gofmt...
GOFMTOUT=$(gofmt -l *go */*go)
if [ "$GOFMTOUT" != "" ] ; then
	echo FAIL: gofmt reports files with formatting inconsistencies - fix with gofmt -w: $GOFMTOUT
	exit 1
fi

pytype src/dovesnap/*py

echo ok
exit 0
