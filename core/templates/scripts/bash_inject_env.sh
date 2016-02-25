#!/bin/bash -x
atmo_user="{{ username }}"
env_file="{{ env_file }}"
env_vars=`cat $env_file`
if [[ $env_vars == *"ATMO_USER="* ]]; then
    sed -i "s/ATMO_USER=.*/ATMO_USER=\"$atmo_user\"/" $env_file
else
    echo "ATMO_USER=\"$atmo_user\"" >> $env_file
fi
