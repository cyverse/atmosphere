#!/usr/bin/env bash

# Local Development Note:
#
# if you have chosen a $ATMOSPHERE_HOME other than the default,
# then `export` ATMOSPHERE_HOME for that location to get the
# expected behavior.

# this removes all pyc file under this location - recursively
if [ -z ${ATMOSPHERE_HOME+x} ]; then
  ATMOSPHERE_HOME=/opt/dev/atmosphere;
fi

export ATMOSPHERE_HOME;

find ${ATMOSPHERE_HOME} -name "*.bak.*" -exec rm '{}' ';'
