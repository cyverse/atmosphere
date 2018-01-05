#!/bin/bash
HOME="/opt/dev/atmosphere"
VIRTUAL="/opt/env/atmo"
export DJANGO_SETTINGS_MODULE="atmosphere.settings"
export PYTHONPATH="$HOME:$PYTHONPATH"
cd $HOME
. $VIRTUAL/bin/activate
echo $PATH
echo $PYTHONPATH
$HOME/scripts/application_sync_providers.py --glance-client-versions '{"4": 2.5, "5": 2.5}' 4 5