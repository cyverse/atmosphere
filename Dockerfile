# Docker Container for Atmosphere
FROM ubuntu:18.04

# Set environment
SHELL ["/bin/bash", "-c"]

# Install dependencies with apt
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y  \
      apt-transport-https \
      build-essential \
      git \
      g++ \
      libffi-dev \
      libguestfs-tools \
      libldap2-dev \
      libpq-dev \
      libsasl2-dev \
      libssl-dev \
      libxml2-dev \
      libxslt1-dev \
      locales \
      make \
      netcat \
      openssl \
      postgresql-client \
      python \
      python-dev \
      python-m2crypto \
      python-pip \
      python-psycopg2 \
      python-setuptools \
      python-tk \
      redis-server \
      sendmail \
      ssh \
      sudo \
      swig \
      ufw \
      uwsgi \
      uwsgi-plugin-python \
      zlib1g-dev && \
      apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    locale-gen en_US.UTF-8

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Create PID and log directories for uWSGI
RUN mkdir -p /run/uwsgi/app/atmosphere /var/log/uwsgi && \
    chown -R www-data:www-data /run/uwsgi/app/ /var/log/uwsgi && \
    touch /var/log/uwsgi/atmosphere.log

# Clone repos and pip install requirements
RUN mkdir /opt/env && \
    pip install --upgrade pip==9.0.3 virtualenv &&\
    virtualenv /opt/env/atmosphere &&\
    ln -s /opt/env/atmosphere/ /opt/env/atmo

COPY . /opt/dev/atmosphere
WORKDIR /opt/dev/atmosphere

# Install initd files
RUN cp docker/flower.initd /etc/init.d/flower && \
    cp docker/celeryd.initd /etc/init.d/celeryd && \
    cp docker/celerybeat.initd /etc/init.d/celerybeat && \
    chmod -R 755 /etc/init.d

# Setup uwsgi
RUN mkdir -p /etc/uwsgi/apps-available /etc/uwsgi/apps-enabled && \
    cp docker/uwsgi.ini /etc/uwsgi/apps-available/atmosphere.ini && \
    ln -s /etc/uwsgi/apps-available/atmosphere.ini /etc/uwsgi/apps-enabled/atmosphere.ini

RUN source /opt/env/atmo/bin/activate && pip install -r requirements.txt

RUN useradd user

# Prepare entrypoint
RUN cp docker/web_shell_no_gateone.yml /opt/web_shell_no_gateone.yml && \
    mkdir -p /root/.ssh && \
    cp docker/ssh.config /root/.ssh/config && \
    cp docker/entrypoint.sh /root/entrypoint.sh && \
    cp docker/test.sh /root/test.sh && \
    chmod +x /root/entrypoint.sh && \
    chmod +x /root/test.sh && \
    echo "source /opt/env/atmo/bin/activate" >> /root/.bashrc
ENTRYPOINT ["/root/entrypoint.sh"]
