#!/bin/bash
HOME="/opt/dev/atmosphere"
VIRTUAL="/opt/env/atmo"
export DJANGO_SETTINGS_MODULE="atmosphere.settings"
export PYTHONPATH="$HOME:$PYTHONPATH"
cd $HOME
. $VIRTUAL/bin/activate
echo $PATH
echo $PYTHONPATH
python $HOME/scripts/switch_user_quota.py $@
