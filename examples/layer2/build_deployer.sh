#!/bin/bash

set -exu

source l2/.env

docker build --build-arg SOLC_VERSIONS="$SOLC_VERSIONS" -t sc-deployer -f Dockerfile.deployer .