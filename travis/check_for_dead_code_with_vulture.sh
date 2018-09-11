#!/bin/bash

#
# This script uses vulture to ensure that dead code is not included in the
# project.
#
# Because python is a dynamic language and vulture is a static analysis tool,
# vulture performs only a best effort attempt. Sometimes it will report dead
# code that is actually in use.
#
# Vulture supports a whitelist, which instructs it that certain names are
# indeed still in use. You can use the following command to produce a
# whitelist with all the names it currently thinks refer to dead code
# $ vulture --make-whitelist .
#
# Any entries that you would like to whitelist should be copied from that
# output and included in the .vulture-whitelist file, which is the current
# whitelist.

function main {

    vulture --min-confidence 61 .vulture-whitelist  $(git ls-files | grep 'py$')

    if [[ $? -ne 0 ]]; then
        warn_dead_code_found;
        exit 1;
    fi;

    echo_success_message;
}

function warn_dead_code_found {
    warn "vulture reported dead code!" >&2;
    echo "If the code is not dead you will need to update the whitelist." \
         "See $0" >&2;
}

function echo_success_message {
    local default="\e[0m" green="\e[32m";
    printf "${green}";
    echo "No dead code found!" >&2;
    printf "${default}";
}

function warn {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "$@";
    printf "${default}";
}

main
