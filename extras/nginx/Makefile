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
TROPOSPHERE_PATH=/opt/dev/troposphere

SITES_AVAILABLE_DIR=/etc/nginx/sites-available
SITES_ENABLED_DIR=/etc/nginx/sites-enabled

DHPARAM=/etc/ssl/certs/dhparam.pem
KEY_SIZE=2048

CONFIG=$(ATMOSPHERE_PATH)/extras/nginx/atmo.conf

.PHONY: all clean

all: deploy

copy:
	cp $(CONFIG).dist $(CONFIG)

$(DHPARAM):
	openssl dhparam -out $(DHPARAM) $(KEY_SIZE)

setup: copy
	sed -i "s#@ATMOSPHERE_PATH#$(ATMOSPHERE_PATH)#g" $(CONFIG)
	sed -i "s#@TROPOSPHERE_PATH#$(TROPOSPHERE_PATH)#g" $(CONFIG)
	sed -i "s#@LEADERBOARD_URL#$(LEADERBOARD_URL)#g" $(CONFIG)
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(CONFIG)
	sed -i "s#@COMBINED_CERT_PATH#$(COMBINED_CERT_PATH)#g" $(CONFIG)
	sed -i "s#@KEY_PATH#$(KEY_PATH)#g" $(CONFIG)
	sed -i "s#@DHPARAM#$(DHPARAM)#g" $(CONFIG)

$(COMBINED_CERT_PATH):
	cat $(CERT_PATH) $(BUNDLE_PATH) > $(COMBINED_CERT_PATH)

deploy: $(COMBINED_CERT_PATH) setup $(DHPARAM) unlink
	mkdir -p $(SITES_AVAILABLE_DIR)
	mkdir -p $(SITES_ENABLED_DIR)
	ln -fs $(ATMOSPHERE_PATH)/extras/nginx/atmo.conf $(SITES_AVAILABLE_DIR)/atmo.conf
	ln -fs $(SITES_AVAILABLE_DIR)/atmo.conf $(SITES_ENABLED_DIR)/atmo.conf

unlink:
	-rm $(SITES_ENABLED_DIR)/atmo.conf
	-rm $(SITES_AVAILABLE_DIR)/atmo.conf

test:
	service nginx configtest

restart:
	service nginx restart

clean: unlink
	rm -f $(CONFIG) $(DHPARAM)
