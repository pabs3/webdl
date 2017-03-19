#!/bin/bash

(
if ! flock -n -x 200; then
    exit 0
fi

umask 0002

cd ~/dev/webdl

echo "INFO git pull --ff-only"
git pull --ff-only

echo "INFO .virtualenv/bin/activate"
source .virtualenv/bin/activate

echo "INFO Running autograbber"
./autograbber.py "$@"

) 200>"/tmp/webdl-autograbber-lock"
