# Systemd

This directory contains Systemd service files for Atmosphere services.

### Description

To use Systemd and these files:
```
systemctl start <service_name>
systemctl stop <service_name>
systemctl restart <service_name>
```

#### `atmosphere-full.service`
This service starts all of Atmosphere, including `uwsgi`, `nignx`, `celeryd`, `celerybeat`, `flower`, and `redis`.

On stop and restart, it stops/restarts all except for `redis`.

#### `atmosphere.service`
This service starts `nginx` and `uwsgi` for Atmosphere. It will also stop and restart these services.

This service can still be used to if Atmosphere was originally started by `atmopshere-celery.service`:

`systemctl start atmosphere-full`

If you want to restart only `nginx` and `uwsgi`:

`systemctl restart atmosphere`

#### `celerybeat.service`
This service starts and stops `celerybeat`.

#### `celeryd.service`
This service starts and stops `celeryd`.

#### `flower.service`
This service starts and stops `flower`


### Example
If Atmosphere is already fully running and you want to:

Restart only `nginx` and `uwsgi` : `systemctl restart atmosphere`

Restart only `celeryd` : `systemctl restart celeryd`

Restart only `flower` : `systemctl restart flower`

End it all : `systemctl stop atmosphere-full redis-server`
