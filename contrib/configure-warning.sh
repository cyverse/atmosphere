#!/bin/bash

# Does configure error out?
./configure --dry-run &>/dev/null
SUCCESS=$?

if [ $SUCCESS -ne 0 ]; then
   default="\e[0m"
   red="\e[31m"
   printf '['$red'configure-warning.sh hook'$default']: Configure needs to be run.\n'
   printf './configure\n'
fi
