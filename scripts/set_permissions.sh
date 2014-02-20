#!/usr/bin/env bash

export ATMOSPHERE_HOME=/opt/dev/atmosphere

chmod -R g+w ${ATMOSPHERE_HOME}

chmod -R 644 ${ATMOSPHERE_HOME}/extras/ssh

chmod 755 ${ATMOSPHERE_HOME}/extras/ssh

chmod -R 600 ${ATMOSPHERE_HOME}/extras/ssh/id_rsa

chown -R www-data:core-services ${ATMOSPHERE_HOME}

chown -R root:root ${ATMOSPHERE_HOME}/extras/apache

chown -R root:root ${ATMOSPHERE_HOME}/extras/ssh

