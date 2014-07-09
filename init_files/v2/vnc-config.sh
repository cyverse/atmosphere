#!/bin/bash

echo Configuring vnc.

echo "# vncserver common.custom configuration.
SecurityTypes=RA2
Permissions=root:f,%core-services:f,:f
EnableAutoUpdateChecks=1

# Atmosphere port configuration.
HttpPort=5904
-geometry 1280x800
-randr 1024x768,800x600,1280x800,1280x960,1280x1024,1680x1050,1920x1080,1920x1200,3360x1050,1024x700,1200x740,1600x1000,1600x1200,3200x1000,3200x1200
" > /etc/vnc/config.custom

echo Configured vnc.


