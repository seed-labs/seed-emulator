#!/bin/bash

docker compose up -d seedemu_internetmap
ls | grep -Ev '.yml$|^dummies$|^morris|^z_start|^z_build' | xargs -n10 -exec docker compose up -d
