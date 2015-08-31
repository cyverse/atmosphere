nginx configuration
===================
Configure atmosphere to use nginx. The Makefile uses defaults for a common configuration of Atmosphere.

# Instructions

1. Configure the [nginx] variable section in the project's variables.ini file.

2. Verify or update the atmo.uwsgi.ini and trop.uwsgi.ini to use unix file sockets
   instead of localhost proxying.

3. Stop apache2, if it's running.

4. Generate the Makefile and run the make command.

```bash
cd /opt/dev/atmosphere
./scripts/generate_configs.py -c nginx
cd ./extras/nginx
make
```

5. Run make test command to verify your nginx config.

```bash
make test
```

6. Start nginx.

```bash
service nginx start
```
