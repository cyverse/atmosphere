#!/bin/bash
HOME="/opt/dev/atmosphere"
VIRTUAL="/opt/env/atmosphere"
export DJANGO_SETTINGS_MODULE="atmosphere.settings"
export PYTHONPATH="$HOME:$PYTHONPATH"
cd $HOME
. $VIRTUAL/bin/activate
python $HOME/scripts/add_new_accounts.py

