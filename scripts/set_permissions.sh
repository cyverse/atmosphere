#!/usr/bin/env bash

if [[ $EUID -ne 0 ]]; then
    echo "You must be a root user to set these permissions"
    exit 1
fi

if [ "$#" -ge 1 ]; then
  export ATMOSPHERE_HOME="$1"
else
  export ATMOSPHERE_HOME=/opt/dev/atmosphere
fi
echo "Using Atmo HOME: $ATMOSPHERE_HOME"

chmod -R g+w ${ATMOSPHERE_HOME}

chmod -R 644 ${ATMOSPHERE_HOME}/extras/ssh

chmod 755 ${ATMOSPHERE_HOME}/extras/ssh

chmod -R 600 ${ATMOSPHERE_HOME}/extras/ssh/id_rsa

chown -R www-data:core-services ${ATMOSPHERE_HOME}

chown -R www-data:core-services ${ATMOSPHERE_HOME}/extras/apache

chown -R root:root ${ATMOSPHERE_HOME}/extras/ssh

chown root:root ${ATMOSPHERE_HOME}/extras/logrotate.atmosphere

chmod 644 ${ATMOSPHERE_HOME}/extras/logrotate.atmosphere
