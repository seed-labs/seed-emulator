#!/bin/bash

ls | grep -Ev '.yml$|^dummies$|^z_start' | xargs -n10 -exec docker-compose up -d
