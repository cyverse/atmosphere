#!/usr/bin/env bash

export ATMOSPHERE_HOME=/opt/dev/atmosphere

chmod -R g+w ${ATMOSPHERE_HOME}

chown -R www-data:core-services ${ATMOSPHERE_HOME}

chown -R root:root ${ATMOSPHERE_HOME}/extras/apache

chown -R postgres:postgres ${ATMOSPHERE_HOME}/extras/sql
