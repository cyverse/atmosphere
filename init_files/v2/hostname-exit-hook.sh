#!/bin/bash

# Function: get_hostname()
# Description: Gets the hostname, depending on the distro
get_hostname() {
   local is_centos5=0
   if [ -e /etc/redhat-release ]; then
      s=$(grep 'CentOS release 5' /etc/redhat-release)
      if [ $? -eq 0 ]; then
         is_centos5=1
      fi
   fi

   if [ $is_centos5 -eq 1 ]; then
      hostname_value=$(curl -s 'http://169.254.169.254/openstack/latest/meta_data.json' | python -c'from simplejson.tool import main; main()' | sed -n -e '/"public-hostname":/ s/^.*"\(.*\)".*/\1/p')
   else
      hostname_value=$(curl -s 'http://169.254.169.254/openstack/latest/meta_data.json' | python -mjson.tool | sed -n -e '/"public-hostname":/ s/^.*"\(.*\)".*/\1/p')
   fi
}

MAX_ATTEMPTS=5

retry=0
hostname_value=""

echo $(date +"%m%d%y %H:%M:%S") "dhclient hostname hook started" >>/var/log/atmo/dhcp_hostname.log

while [ $retry -lt $MAX_ATTEMPTS -a -z "$hostname_value" ]; do
    ((retry++))
    echo $(date +"%m%d%y %H:%M:%S") "   Attempt #${retry}" >>/var/log/atmo/dhcp_hostname.log
    # Note: gobal hostname_value is returned
    get_hostname
    sleep 1
done

if [[ -z $hostname_value ]]; then
    echo $(date +"%m%d%y %H:%M:%S") "   Hostname could not be determined. using `hostname`" >>/var/log/atmo/dhcp_hostname.log
else
    if [[ $hostname_value  == 129.114.5.* ]]; then
       hostname "austin5-"$(echo $hostname_value | awk 'BEGIN {FS="."};{print $4}')".cloud.bio.ci"
    else
       hostname $hostname_value
    fi
    echo $(date +"%m%d%y %H:%M:%S") "   Hostname has been set to `hostname`" >>/var/log/atmo/dhcp_hostname.log
fi
