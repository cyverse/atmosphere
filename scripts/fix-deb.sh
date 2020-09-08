#!/bin/bash

deb_url='https://github.com/cyverse/atmosphere-ansible/raw/master/ansible/roles/atmo-vnc/files/VNC-Server-5.2.3-Linux-x64.deb'
deb_path='/opt/dev/atmosphere-ansible/ansible/roles/atmo-vnc/files/VNC-Server-5.2.3-Linux-x64.deb'

if [ ! -f "$deb_path" -o ! -s "$deb_path" ]; then
	echo "$(date): '$deb_path' does not exist"
	wget --quiet $deb_url -O $deb_path

	# Now check again
	if [ ! -f "$deb_path" ]; then
                echo "$(date): '$deb_path' still does not exist. Try again..."
	else
	        echo "$(date): '$deb_path' now exists. Fixed!"
        fi
fi
