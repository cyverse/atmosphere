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

SITE_CONF_FILE=site.conf
SITE_CONF_PATH=$(ATMOSPHERE_PATH)/extras/nginx/$(SITE_CONF_FILE)
ATMO_CONF_FILE=atmo.conf
ATMO_CONF_PATH=$(ATMOSPHERE_PATH)/extras/nginx/locations/$(ATMO_CONF_FILE)
FLOWER_CONF_FILE=flower.conf
FLOWER_CONF_PATH=$(ATMOSPHERE_PATH)/extras/nginx/locations/$(FLOWER_CONF_FILE)
JENKINS_CONF_FILE=jenkins.conf
JENKINS_CONF_PATH=$(ATMOSPHERE_PATH)/extras/nginx/locations/$(JENKINS_CONF_FILE)
LB_CONF_FILE=leaderboard.conf
LB_CONF_PATH=$(ATMOSPHERE_PATH)/extras/nginx/locations/$(LB_CONF_FILE)
# ... more configs.

.PHONY: all clean

all: deploy

copy:
	cp $(SITE_CONF_PATH).dist $(SITE_CONF_PATH)
	cp $(ATMO_CONF_PATH).dist $(ATMO_CONF_PATH)
	cp $(FLOWER_CONF_PATH).dist $(FLOWER_CONF_PATH)
	cp $(JENKINS_CONF_PATH).dist $(JENKINS_CONF_PATH)
	cp $(LB_CONF_PATH).dist $(LB_CONF_PATH)

$(DHPARAM):
	openssl dhparam -out $(DHPARAM) $(KEY_SIZE)

setup: copy setup-atmo setup-flower setup-jenkins setup-lb
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(SITE_CONF_PATH)
	sed -i "s#@COMBINED_CERT_PATH#$(COMBINED_CERT_PATH)#g" $(SITE_CONF_PATH)
	sed -i "s#@KEY_PATH#$(KEY_PATH)#g" $(SITE_CONF_PATH)
	sed -i "s#@DHPARAM#$(DHPARAM)#g" $(SITE_CONF_PATH)

setup-atmo:
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(ATMO_CONF_PATH)
	sed -i "s#@ATMOSPHERE_PATH#$(ATMOSPHERE_PATH)#g" $(ATMO_CONF_PATH)

setup-flower:
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(FLOWER_CONF_PATH)

setup-jenkins:
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(JENKINS_CONF_PATH)

setup-lb:
	sed -i "s#@LEADERBOARD_URL#$(LEADERBOARD_URL)#g" $(LB_CONF_PATH)

$(COMBINED_CERT_PATH):
	cat $(CERT_PATH) $(BUNDLE_PATH) > $(COMBINED_CERT_PATH)

deploy: $(COMBINED_CERT_PATH) setup $(DHPARAM) unlink deploy-atmo deploy-flower deploy-jenkins deploy-lb
	mkdir -p $(SITES_AVAILABLE_DIR)
	mkdir -p $(SITES_ENABLED_DIR)
	ln -fs $(ATMOSPHERE_PATH)/extras/nginx/site.conf $(SITES_AVAILABLE_DIR)/$(SITE_CONF_FILE)
	ln -fs $(SITES_AVAILABLE_DIR)/site.conf $(SITES_ENABLED_DIR)/$(SITE_CONF_FILE)
	ln -fs $(ATMOSPHERE_PATH)/extras/init.d/atmosphere.uwsgi+nginx /etc/init.d/atmosphere

deploy-atmo:
	mkdir -p $(LOCATIONS_DIR)
	ln -fs $(ATMO_CONF_PATH) $(LOCATIONS_DIR)/$(ATMO_CONF_FILE)

deploy-flower:
	mkdir -p $(LOCATIONS_DIR)
	ln -fs $(FLOWER_CONF_PATH) $(LOCATIONS_DIR)/$(FLOWER_CONF_FILE)

deploy-jenkins:
	mkdir -p $(LOCATIONS_DIR)
	ln -fs $(JENKINS_CONF_PATH) $(LOCATIONS_DIR)/$(JENKINS_CONF_FILE)

deploy-lb:
	mkdir -p $(LOCATIONS_DIR)
	ln -fs $(LB_CONF_PATH) $(LOCATIONS_DIR)/$(LB_CONF_FILE)

unlink: unlink-atmo unlink-flower unlink-jenkins unlink-lb
	-rm $(SITES_ENABLED_DIR)/$(SITE_CONF_FILE)
	-rm $(SITES_AVAILABLE_DIR)/$(SITE_CONF_FILE)

unlink-atmo:
	-rm $(LOCATIONS_DIR)/$(ATMO_CONF_FILE)

unlink-flower:
	-rm $(LOCATIONS_DIR)/$(FLOWER_CONF_FILE)

unlink-jenkins:
	-rm $(LOCATIONS_DIR)/$(JENKINS_CONF_FILE)

unlink-lb:
	-rm $(LOCATIONS_DIR)/$(LB_CONF_FILE)

test:
	service nginx configtest

restart:
	service nginx restart

clean: unlink
	-rm $(COMBINED_CERT_PATH)
	-rm $(SITE_CONF_PATH)
	-rm $(ATMO_CONF_PATH)
	-rm $(DHPARAM)
	-rm /etc/init.d/atmosphere
