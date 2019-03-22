#!/bin/bash

function check_for_repo() {
  if test ! -d /opt/dev/$1/.git/
  then
    >&2 echo "ERROR: $1 repository does not exist and is required"
    return 1
  else
    echo "$1 repository exists. Continuing..."
    return 0
  fi
}

# Check that all necessary repositories exists
check_for_repo atmosphere || exit 1
check_for_repo atmosphere-ansible || exit 1
check_for_repo atmosphere-docker-secrets || exit 1

MANAGE_CMD="/opt/env/atmo/bin/python /opt/dev/atmosphere/manage.py"

# Setup Atmosphere
source /opt/env/atmo/bin/activate && \
pip install -r /opt/dev/atmosphere/requirements.txt

# Setup SSH keys
export SECRETS_DIR=/opt/dev/atmosphere-docker-secrets
mkdir -p /opt/dev/atmosphere/extras/ssh
cp $SECRETS_DIR/ssh/id_rsa /opt/dev/atmosphere/extras/ssh/id_rsa
cp $SECRETS_DIR/ssh/id_rsa.pub /opt/dev/atmosphere/extras/ssh/id_rsa.pub
echo -e "Host *\n\tIdentityFile /opt/dev/atmosphere/extras/ssh/id_rsa\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile=/dev/null" >> ~/.ssh/config

# Setup instance deploy automation
cp $SECRETS_DIR/atmosphere-ansible/hosts /opt/dev/atmosphere-ansible/ansible/hosts
cp -r $SECRETS_DIR/atmosphere-ansible/group_vars /opt/dev/atmosphere-ansible/ansible/group_vars

# Link ini files
ln -s $SECRETS_DIR/inis/atmosphere.ini /opt/dev/atmosphere/variables.ini
ln -s $SECRETS_DIR/inis/atmosphere-ansible.ini /opt/dev/atmosphere-ansible/variables.ini
/opt/env/atmo/bin/python /opt/dev/atmosphere/configure
/opt/env/atmo/bin/python /opt/dev/atmosphere-ansible/configure

mkdir -p /opt/dev/atmosphere/logs

source /opt/dev/atmosphere-docker-secrets/env

if [[ $env_type = "dev" ]]
then
  chown -R 1000:1000 /opt/dev/atmosphere
  sed -i "s/^CELERYD_USER=\"www-data\"$/CELERYD_USER=\"user\"/" /etc/init.d/celeryd
  sed -i "s/^CELERYD_GROUP=\"www-data\"$/CELERYD_GROUP=\"1000\"/" /etc/init.d/celeryd
  sed -i "s/^CELERY_USER=\"www-data\"$/CELERY_USER=\"user\"/" /etc/init.d/celerybeat
  sed -i "s/^CELERY_GROUP=\"www-data\"$/CELERY_GROUP=\"1000\"/" /etc/init.d/celerybeat
else
  chown -R www-data:www-data /opt/dev/atmosphere
fi

# Start services
service redis-server start
service celerybeat start
service celeryd start

# Wait for DB to be active
echo "Waiting for postgres..."
while ! nc -z postgres 5432; do sleep 5; done

# Finish Django DB setup
mkdir -p /opt/dev/atmosphere/static
$MANAGE_CMD collectstatic --noinput --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere
$MANAGE_CMD migrate --noinput --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere
$MANAGE_CMD loaddata --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere /opt/dev/atmosphere/core/fixtures/provider.json
$MANAGE_CMD loaddata --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere /opt/dev/atmosphere/core/fixtures/quota.json
$MANAGE_CMD loaddata --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere /opt/dev/atmosphere/core/fixtures/pattern_match.json
$MANAGE_CMD loaddata --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere /opt/dev/atmosphere/core/fixtures/boot_script.json
$MANAGE_CMD createcachetable --settings=atmosphere.settings --pythonpath=/opt/dev/atmosphere atmosphere_cache_requests

chmod 600 /opt/dev/atmosphere/extras/ssh/id_rsa

if [[ $env_type = "dev" ]]
then
  cp /opt/web_shell_no_gateone.yml /opt/dev/atmosphere-ansible/ansible/playbooks/instance_deploy/41_shell_access.yml
  chown -R 1000:1000 /opt/dev/atmosphere
  echo "Starting Django Python..."
  sudo su -l user -s /bin/bash -c "/opt/env/atmo/bin/python /opt/dev/atmosphere/manage.py runserver 0.0.0.0:8000"
else
  sudo su -l www-data -s /bin/bash -c "UWSGI_DEB_CONFNAMESPACE=app UWSGI_DEB_CONFNAME=atmosphere /opt/env/atmo/bin/uwsgi --ini /usr/share/uwsgi/conf/default.ini --ini /etc/uwsgi/apps-enabled/atmosphere.ini"
fi
