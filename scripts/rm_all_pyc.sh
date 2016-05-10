#!/usr/bin/env bash
# this removes all pyc file under this location - recursively

export ATMOSPHERE_HOME=/opt/dev/atmosphere # For dalloway, arturo

find ${ATMOSPHERE_HOME} -name "*.pyc" -exec rm '{}' ';'
find ${ATMOSPHERE_HOME} -name "*.pyo" -exec rm '{}' ';'
