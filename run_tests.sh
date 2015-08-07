#!/bin/bash
set -e
VIRTUALENV=/opt/env/atmo
SCRIPT_DIR=$(dirname `readlink -f $0`)
source $VIRTUALENV/bin/activate
$SCRIPT_DIR/manage.py test --noinput --settings=atmosphere.settings -v2 -- $@
