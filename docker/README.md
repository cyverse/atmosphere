# Atmosphere


This container runs Atmosphere, uWSGI, and Celery.


If using the local development branch of secrets, Atmosphere is run using Django's `runserver` command instead of uWSGI in order to enable automatic reloading of code changes.


The Dockerfile is based on Ubuntu 14.04 and installs dependencies and static configuration files. Also creates virtualenv but does not install anything to it. Since Atmosphere code and secrets are added at runtime, the entrypoint script will:

  1. Ensure all required git repos are present
  2. Pip install requirements into virtualenv
  3. Copy SSH keys from secrets into Atmosphere and configure SSH settings
  4. Link Atmosphere and Atmosphere-Ansible ini settings from secrets into the repositories and run the `./configure` script
  5. Change ownership of Atmosphere directory to be owned by new group with GID 2000 to allow `www-data` to use the files without changing user ownership
  6. Start celeryd, celerybeat, and redis
  7. Run Django migrations
  8. Start uWSGI or Django `runserver` depending on use case
