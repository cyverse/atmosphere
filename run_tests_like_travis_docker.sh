#!/usr/bin/env bash


# BEWARE! This script:
# - Drops two databases
# - Deletes a user
# - Overwrites your variables.ini, local.py, secrets.py, etc.
# - Forcibly updates packages in your virtual environment
#
# Read it.

# Usage:
# 0. Start a bash session in your atmosphere docker container
#    (docker exec -it <container_name> /bin/bash)
# 1. ./run_tests_like_travis.sh [cyverse|jetstream]

set -e
set -x

# Install pre-dependencies
apt-get update && apt-get install -y postgresql

DISTRIBUTION=${1:-cyverse}
VENV_PATH=/opt/env/atmo-test
ATMO_PATH=/opt/dev/atmosphere
SUDO_POSTGRES=''  # Leave empty if sudo not required to run dropdb, createdb & psql
PIP_TOOLS_VERSION=1.9.0

cd $ATMO_PATH
if [ ! -d "$VENV_PATH" ]; then
    virtualenv "$VENV_PATH";
fi
source $VENV_PATH/bin/activate

# pip install -U pip setuptools pip-tools=="$PIP_TOOLS_VERSION"
# pip-sync dev_requirements.txt
pip install -r dev_requirements.txt
echo "DROP DATABASE IF EXISTS atmosphere_db" | ./manage.py dbshell
echo "DROP DATABASE IF EXISTS test_atmosphere_db" | ./manage.py dbshell
echo "DROP USER IF EXISTS atmosphere_db_user" | ./manage.py dbshell
echo "CREATE USER atmosphere_db_user WITH PASSWORD 'atmosphere_db_pass' CREATEDB;" | ./manage.py dbshell
echo "CREATE DATABASE atmosphere_db WITH OWNER atmosphere_db_user;" | ./manage.py dbshell


rm variables.ini
cp ./variables.ini.dist ./variables.ini
patch variables.ini variables_for_testing_${DISTRIBUTION}_docker.ini.patch
./configure
# ./travis/check_properly_generated_requirements.sh

python manage.py test --keepdb
rm -f rerun_failing.features
python manage.py behave --keepdb --tags ~@skip-if-${DISTRIBUTION}

# Restore previous variables.ini
rm variables.ini
ln -s ../atmosphere-docker-secrets/inis/atmosphere.ini variables.ini
./configure
