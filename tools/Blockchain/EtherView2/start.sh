#!/bin/sh
while true; do FLASK_APP=server flask run --host=0.0.0.0 --port=3000; done
