#!/usr/bin/env python3
# update docker-compose.yaml with release version or dev version.
import json
import sys
import urllib.request
from collections import OrderedDict

import ruamel.yaml

VERSION_FILE = '../main.go'
DOCKER_COMPOSE = '../docker-compose.yml'
with open(VERSION_FILE, 'r') as f:
    for line in f:
        if line.startswith('\tversion = '):
            RELEASE_VER = line.split('"')[1]
DEV = RELEASE_VER.endswith('.dev')

# For dev versions, add this config.
DEV_SERVICE_OVERRIDE = {
    'plugin': {'build': {'context': '.'}},
}
# For non-dev versions, delete this config.
NON_DEV_SERVICE_DELETE = {
    'plugin': ['build'],
}

# Broadly preserves formatting.
yaml = ruamel.yaml.YAML()
assert not yaml.preserve_quotes
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=2, offset=2)
dc = yaml.load(
    open(DOCKER_COMPOSE).read())
for service, service_config in dc['services'].items():
    image, _ = service_config['image'].split(':')
    if DEV:
        version = 'latest'
        if service in DEV_SERVICE_OVERRIDE:
            service_config.update(DEV_SERVICE_OVERRIDE[service])
    else:
        version = 'v' + RELEASE_VER
        del_keys = NON_DEV_SERVICE_DELETE.get(service, None)
        if del_keys:
            for del_key in del_keys:
                if del_key in service_config:
                    del service_config[del_key]
    if service == 'plugin':
        service_config['image'] = ':'.join((image, version))


yaml.dump(dc, open(DOCKER_COMPOSE, 'w'))
