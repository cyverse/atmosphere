SERVER_URL=
LEADERBOARD_URL=
CERT_FILE=
KEY_FILE=

PATH_TO_ATMOSPHERE=/opt/dev/atmosphere
PATH_TO_TROPOSPHERE=/opt/dev/troposphere

SITES_DIR=/etc/nginx/sites-enabled
CONFIG=$(PATH_TO_ATMOSPHERE)/extras/nginx/atmo.conf

DHPARAM=/etc/ssl/certs/dhparam.pem
KEY_SIZE=4098

.PHONY: all clean

all: deploy

copy:
	cp $(CONFIG).dist $(CONFIG)

dhparam:
	openssl dhparam -out $(DHPARAM) $(KEY_SIZE)

setup: copy
	sed -i "s#@PATH_TO_ATMOSPHERE#$(PATH_TO_ATMOSPHERE)#g" $(CONFIG)
	sed -i "s#@PATH_TO_TROPOSPHERE#$(PATH_TO_TROPOSPHERE)#g" $(CONFIG)
	sed -i "s#@LEADERBOARD_URL#$(LEADERBOARD_URL)#g" $(CONFIG)
	sed -i "s#@SERVER_URL#$(SERVER_URL)#g" $(CONFIG)
	sed -i "s#@CERT_FILE#$(CERT_FILE)#g" $(CONFIG)
	sed -i "s#@KEY_FILE#$(KEY_FILE)#g" $(CONFIG)
	sed -i "s#@DHPARAM#$(DHPARAM)#g" $(CONFIG)

deploy: setup dhparam unlink
	mkdir -p $(SITES_DIR)
	ln -s $(PATH_TO_ATMOSPHERE)/extras/nginx/atmo.conf $(SITES_DIR)/atmo.conf

unlink:
	rm -f $(SITES_DIR)/atmo.conf

test:
	service nginx configtest

restart:
	service nginx restart

clean: unlink
	rm -f $(CONFIG) $(DHPARAM)

