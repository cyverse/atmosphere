uWSGI configuration
===================

uWSGI configuration files for Atmosphere. Note it doesn't require package install. Only pip install.


# Details

* uwsgi.conf is an upstart conf that should be linked in /etc/init/uwsgi.conf.
* atmo.uwsgi.ini is a uwsgi conf that should be linked in /etc/uwsgi/apps-enabled/

# Notes

After the *uwsgi.conf* has been linked the upstart configuration should be reloaded.

```bash
initctl reload-configuration
```
