SERVER_URL=$(shell hostname -f)
LEADERBOARD_URL=wesley.iplantcollaborative.org

CERT_DIR=/etc/ssl/certs
CERT_FILE=iplantc.org.crt
CERT_PATH=$(CERT_DIR)/$(CERT_FILE)

COMBINED_CERT_FILE=iplantc_combined.crt
COMBINED_CERT_PATH=$(CERT_DIR)/$(COMBINED_CERT_FILE)

BUNDLE_FILE=gd_bundle.crt
BUNDLE_PATH=$(CERT_DIR)/$(BUNDLE_FILE)

KEY_FILE=iplantc.key
KEY_PATH=/etc/ssl/private/$(KEY_FILE)

ATMOSPHERE_PATH=/opt/dev/atmosphere

SITES_AVAILABLE_DIR=/etc/nginx/sites-available
SITES_ENABLED_DIR=/etc/nginx/sites-enabled
LOCATIONS_DIR=/etc/nginx/locations

DHPARAM=/etc/ssl/certs/dhparam.pem
KEY_SIZE=2048

SITE_CONF=$(ATMOSPHERE_PATH)/extras/nginx/site.conf
ATMO_CONF_FILE=atmo.conf
ATMO_CONF_PATH=$(ATMOSPHERE_PATH)/extras/nginx/locations/$(ATMO_CONF_FILE)
# ... more configs.

.PHONY: all clean

all: deploy

copy:
	cp $(SITE_CONF).dist $(SITE_CONF)
	cp $(ATMO_CONF_PATH).dist $(ATMO_CONF_PATH)

$(DHPARAM):
	openssl dhparam -out $(DHPARAM) $(KEY_SIZE)

setup: copy atmo-setup
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(SITE_CONF)
	sed -i "s#@COMBINED_CERT_PATH#$(COMBINED_CERT_PATH)#g" $(SITE_CONF)
	sed -i "s#@KEY_PATH#$(KEY_PATH)#g" $(SITE_CONF)
	sed -i "s#@DHPARAM#$(DHPARAM)#g" $(SITE_CONF)
#TODO	sed -i "s#@LEADERBOARD_URL#$(LEADERBOARD_URL)#g" $(CONFIG)

atmo-setup:
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(ATMO_CONF_PATH)
	sed -i "s#@ATMOSPHERE_PATH#$(ATMOSPHERE_PATH)#g" $(ATMO_CONF_PATH)

$(COMBINED_CERT_PATH):
	cat $(CERT_PATH) $(BUNDLE_PATH) > $(COMBINED_CERT_PATH)

deploy: $(COMBINED_CERT_PATH) setup $(DHPARAM) unlink atmo-deploy
	mkdir -p $(SITES_AVAILABLE_DIR)
	mkdir -p $(SITES_ENABLED_DIR)
	ln -fs $(ATMOSPHERE_PATH)/extras/nginx/site.conf $(SITES_AVAILABLE_DIR)/site.conf
	ln -fs $(SITES_AVAILABLE_DIR)/site.conf $(SITES_ENABLED_DIR)/site.conf
	ln -fs $(ATMOSPHERE_PATH)/extras/init.d/atmosphere.uwsgi+nginx /etc/init.d/atmosphere

atmo-deploy:
	mkdir -p $(LOCATIONS_DIR)
	ln -fs $(ATMO_CONF_PATH) $(LOCATIONS_DIR)/$(ATMO_CONF_FILE)

unlink: unlink-atmo
	-rm $(SITES_ENABLED_DIR)/site.conf
	-rm $(SITES_AVAILABLE_DIR)/site.conf

unlink-atmo:
	-rm $(LOCATIONS_DIR)/$(ATMO_CONF_FILE)

test:
	service nginx configtest

restart:
	service nginx restart

clean: unlink
	-rm $(COMBINED_CERT_PATH)
	-rm $(SITE_CONF)
	-rm $(ATMO_CONF_PATH)
	-rm $(DHPARAM)
	-rm /etc/init.d/atmosphere
