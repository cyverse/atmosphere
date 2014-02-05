#!/bin/bash
hostname_value=`curl -s "http://169.254.169.254/openstack/latest/meta_data.json" | python -mjson.tool | sed -n -e '/"public-hostname":/ s/^.*"\(.*\)".*/\1/p'`
if [[ -z $hostname_value ]]; then
    echo "Hostname could not be determined. using `hostname`"
else
    hostname $hostname_value
    echo "Hostname has been set to `hostname`"
fi

