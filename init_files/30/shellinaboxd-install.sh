#!/bin/bash

cd $HOME

mkdir -p shellinaboxd_install

cd shellinaboxd_install

SHELL_INSTALL_HOME=`pwd`
shellinaboxfile=shellinabox-2.14.tar.gz
shellinaboxlocation=${SHELL_INSTALL_HOME}/${shellinaboxfile}
shellinaboxdir=`basename ${shellinaboxfile} .tar.gz`

/usr/bin/wget -O${shellinaboxlocation} http://shellinabox.googlecode.com/files/${shellinaboxfile} #2>&1 # &>/dev/null
echo Downloaded shellinabox.

if [ -f  "${shellinaboxlocation}" ]; then
    /bin/tar xfz ${shellinaboxlocation} #2>&1 # &>/dev/null 
    echo Uncompressed and untared shellinabox.
else
    echo File not found.
fi

echo "
./configure;make;make install
"

cd ${SHELL_INSTALL_HOME}/${shellinaboxdir} #2>&1 #&>/dev/null

echo "---
 shellinabox/vt100.jspp | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)

diff --git a/shellinabox/vt100.jspp b/shellinabox/vt100.jspp
index 7a72d0c..578a1b6 100755
--- a/shellinabox/vt100.jspp
+++ b/shellinabox/vt100.jspp
@@ -2898,10 +2898,10 @@ VT100.prototype.keyDown = function(event) {
     event.keyCode == 226;
   var normalKey                 =
     alphNumKey                                   ||
-    event.keyCode ==  59 || event.keyCode ==  61 ||
+    event.keyCode >=  59 && event.keyCode <=  64 ||
     event.keyCode == 106 || event.keyCode == 107 ||
     event.keyCode >= 109 && event.keyCode <= 111 ||
-    event.keyCode >= 186 && event.keyCode <= 192 ||
+    event.keyCode >= 160 && event.keyCode <= 192 ||
     event.keyCode >= 219 && event.keyCode <= 223 ||
     event.keyCode == 252;
   try {
-- " > 0001-add-new-keyCodes-used-by-FF15.patch

echo "
patching fix for firefox 15 keyCode changes.
"

patch -p1 < 0001-add-new-keyCodes-used-by-FF15.patch

CONFIG_SHELL=/bin/bash /bin/bash ./configure CONFIG_SHELL=/bin/bash #2>&1 # &>/dev/null

/usr/bin/make #2>&1 # &>/dev/null
/usr/bin/make install ##2>&1 # &>/dev/null
if [ $? -eq 0 ]; then
    echo shellinabox installed!
else
    exit -1
fi

cd ../..

/usr/bin/nohup /usr/local/bin/shellinaboxd -b -t -f beep.wav:/dev/null > /var/log/atmo/shellinaboxd.log 2>&1 &

echo shellinaboxd running.

exit 0
