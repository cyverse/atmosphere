#!/bin/bash
HOME="/opt/dev/atmosphere"
VIRTUAL="/opt/env/atmo"
export DJANGO_SETTINGS_MODULE="atmosphere.settings"
export PYTHONPATH="$HOME:$PYTHONPATH"
cd $HOME
. $VIRTUAL/bin/activate
python $HOME/scripts/enforce_special_allocation_quota.py