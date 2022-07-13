#!/bin/bash

ls | grep 'rs' | xargs -n10 -exec docker-compose up -d
ls | grep 'rnode' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_0' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_3' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_6' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_9' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_1' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_2' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_4' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_5' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_7' | xargs -n10 -exec docker-compose up -d
ls | grep -E 'host_8' | xargs -n10 -exec docker-compose up -d
