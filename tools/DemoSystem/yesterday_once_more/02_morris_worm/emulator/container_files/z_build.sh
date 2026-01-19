#!/bin/bash

docker compose build morris-worm-base
ls | grep -Ev '.yml$|^dummies$|^morris|^z_start|^z_build' | xargs -n20 -exec docker compose build
