#!/bin/bash
hostname_value=`curl -s "http://169.254.169.254/openstack/latest/meta_data.json" | python -c'from simplejson.tool import main; main()' | sed -n -e '/"public-hostname":/ s/^.*"\(.*\)".*/\1/p'`
if [[ -z $hostname_value ]]; then
    echo "[`date`] Hostname could not be determined. using `hostname`" > /var/log/dhcp_hostname.log
else
    hostname $hostname_value
    echo "[`date`] Hostname has been set to `hostname`" > /var/log/dhcp_hostname.log
fi
