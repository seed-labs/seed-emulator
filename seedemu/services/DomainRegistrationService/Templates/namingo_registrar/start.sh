#!/bin/sh
set -eu

__SEED_DATABASE_SETUP__

mkdir -p /var/log/namingo /run/php
__SEED_SERVICES__
__SEED_AUTOMATION__
