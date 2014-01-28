#!/bin/bash  
# Program: NRPE Installation
# Author: Chris LaRose (cjlarose@iplantcollaborative.org)
# Description: Installs nrpe and snmp on Atmosphere VMs running CENTOS 5/RHEL or Ubuntu 12.04 on x84_64 architectures
# Version 2012-08-17

NAGIOS_SERVER=150.135.93.193

get_distro ()
{
        command -v yum > /dev/null
        status=$?
        if [ $status -eq 0 ]
        then
                DISTRO='rhel'
        fi
        command -v apt-get > /dev/null
        status=$?
        if [ $status -eq 0 ]
        then
                DISTRO='ubuntu'
        fi
        if [ ! $DISTRO ]
        then
                echo "Not a supported linux distribution"
                exit 1
        fi
}

get_distro

# install snmpd, nrpe, and nagios plugins
if [ $DISTRO = "ubuntu" ] 
then
	## ubuntu only
	ATMO_COMMANDS_PATH=/etc/nagios/nrpe.d/atmo-commands.cfg
	NRPE_DAEMON=nagios-nrpe-server
	NRPE_USER=nagios
	apt-get update
	apt-get install -y nagios-nrpe-server libnagios-plugin-perl snmpd python-httplib2
else
	## red hat only
	ATMO_COMMANDS_PATH=/etc/nrpe.d/atmo-commands.cfg
	NRPE_DAEMON=nrpe
	NRPE_USER=nrpe
	/usr/bin/yum install -y net-snmp perl-Net-SNMP nrpe nagios-plugins nagios-plugins-disk nagios-plugins-load nagios-plugins-perl nagios-plugins-procs nagios-plugins-users perl-Nagios-Plugin python-simplejson python-httplib2
fi

# determine the location of the nagios plugins 
if [ -d "/usr/lib64/nagios/plugins" ]
then
	PLUGINS_DIR=/usr/lib64/nagios/plugins
elif [ -d "/usr/lib/nagios/plugins" ]
then
	PLUGINS_DIR=/usr/lib/nagios/plugins
else
	echo "Could not find nagios plugins directory"
	exit 1
fi

# edit nrpe configuration to allow nagios server
/bin/sed -i "s/\(allowed_hosts\=\)/\1$NAGIOS_SERVER,/" /etc/nagios/nrpe.cfg

# write check commands for nrpe
/bin/rm -f $ATMO_COMMANDS_PATH
/bin/touch $ATMO_COMMANDS_PATH
echo "command[check_disk]=$PLUGINS_DIR/check_disk -w 20% -c 10% -M" >> $ATMO_COMMANDS_PATH
echo "command[check_load]=$PLUGINS_DIR/check_load -w 15,10,5 -c 30,25,20" >> $ATMO_COMMANDS_PATH
echo "command[check_mem]=$PLUGINS_DIR/check_snmp_mem.pl -H 127.0.0.1 -C iplantsnmp -w 99,0 -c 100,0 -f" >> $ATMO_COMMANDS_PATH
echo "command[check_procs]=$PLUGINS_DIR/check_procs -w 200 -c 300" >> $ATMO_COMMANDS_PATH
echo "command[check_procs_zombie]=$PLUGINS_DIR/check_procs -w 5 -c 10 -s Z" >> $ATMO_COMMANDS_PATH
echo "command[check_users]=$PLUGINS_DIR/check_users -w 5 -c 10" >> $ATMO_COMMANDS_PATH
echo "command[check_connections]=$PLUGINS_DIR/check_connections.pl -w 50 -c 100" >> $ATMO_COMMANDS_PATH
echo "command[check_atmo_idle]=sudo $PLUGINS_DIR/check_atmo_idle.py -w 5 -c 15" >> $ATMO_COMMANDS_PATH

# snmp conf
/bin/rm -f /etc/snmp/snmpd.conf.bak
/bin/mv /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.bak
echo "com2sec notConfigUser 127.0.0.1 iplantsnmp" >> /etc/snmp/snmpd.conf
echo "group   notConfigGroup v1           notConfigUser" >> /etc/snmp/snmpd.conf
echo "group   notConfigGroup v2c           notConfigUser" >> /etc/snmp/snmpd.conf
echo "view all included .1 80" >> /etc/snmp/snmpd.conf
echo 'access notConfigGroup "" any noauth prefix all none none' >> /etc/snmp/snmpd.conf

# Red Hat only: listen on localhost (Ubuntu does this by default)
if [ $DISTRO = "rhel" ] 
then
	echo 'OPTIONS="-Lsd -Lf /dev/null -p /var/run/snmpd.pid -a -x 127.0.0.1"' >> /etc/sysconfig/snmpd.options
fi

# install check_snmp_mem.pl plugin
/bin/rm -f $PLUGINS_DIR/check_snmp_mem.pl
/usr/bin/wget -O $PLUGINS_DIR/check_snmp_mem.pl http://dedalus.iplantcollaborative.org/nagios-plugins/check_snmp_mem.pl
/bin/sed -i "21cuse lib \"$PLUGINS_DIR\";" $PLUGINS_DIR/check_snmp_mem.pl
/bin/chmod +x $PLUGINS_DIR/check_snmp_mem.pl

# install check_connections plugin
/bin/rm -f $PLUGINS_DIR/check_connections.pl
/usr/bin/wget -O $PLUGINS_DIR/check_connections.pl 'http://dedalus.iplantcollaborative.org/nagios-plugins/check_connections.pl'
/bin/sed -i '45cforeach my $entry (split("\\n", `$netstat -wtun | grep -v 127.0.0.1`)) {' $PLUGINS_DIR/check_connections.pl
/bin/chmod +x $PLUGINS_DIR/check_connections.pl

# install check_atmo_idle.py
/bin/rm -f $PLUGINS_DIR/check_atmo_idle.py
/usr/bin/wget -O $PLUGINS_DIR/check_atmo_idle.py 'http://dedalus.iplantcollaborative.org/nagios-plugins/check_atmo_idle.py'
/bin/chmod +x $PLUGINS_DIR/check_atmo_idle.py

# allow the nrpe user to run check_atmo_idle.py as root
/bin/sed -i '/# Begin Nagios/,/# End Nagios/d' /etc/sudoers
echo "# Begin Nagios" >> /etc/sudoers
echo "User_Alias NAGIOS = $NRPE_USER" >> /etc/sudoers
echo "Cmnd_Alias CHECK_ATMO_IDLE = $PLUGINS_DIR/check_atmo_idle.py" >> /etc/sudoers
echo "Defaults:NAGIOS !requiretty" >> /etc/sudoers
echo "NAGIOS    ALL=(ALL)    NOPASSWD: CHECK_ATMO_IDLE, /etc/nagios/, $PLUGINS_DIR" >> /etc/sudoers
echo "# End Nagios" >> /etc/sudoers

# start daemons
/etc/init.d/$NRPE_DAEMON restart
/etc/init.d/snmpd restart

# rhel
if [ $DISTRO = "rhel" ] 
then
	/sbin/chkconfig --levels 2345 nrpe on
	/sbin/chkconfig --levels 2345 snmpd on
fi
