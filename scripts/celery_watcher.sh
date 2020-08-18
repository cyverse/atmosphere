#!/bin/bash

# This script check celery status and restarts it if it isn't running without
# any errors. The output will get sent to whoever is indicated in the crontab.

# get celery status
celery_status=$(service celeryd status)

# check if status != running
echo $celery_status | grep -i 'celeryd is running' &> /dev/null

# restart if stopped or node(s) need restarting
if [ $? != 0 ]; then
        now=$(date +'%A, %m/%d/%y %H:%M %Z')
        echo "Celery check resulted in the following status:"
        echo
        echo $celery_status
        echo
        echo "Would have restarted celery ${now}..."
        #echo "Restarting on ${now}..."
        #celery_status=$(service celeryd restart)
fi

