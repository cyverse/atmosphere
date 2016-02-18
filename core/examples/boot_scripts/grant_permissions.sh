#!/bin/bash -x

# Permissions Granting Script - v1.0
#
# This is a basic 'permissions granting' script to be used as a template
# for image creators, to ensure that their UID is not left on directories
# critical to the success of their image.

main ()
{
    #
    # This is the main function -- These lines will be executed each run
    #

    inject_atmo_vars
    set_directory
}

inject_atmo_vars ()
{
    #
    #
    #NOTE: For now, only $ATMO_USER will be provided to script templates (In addition to the standard 'env')
    #
    #

    # Source the .bashrc -- this contains $ATMO_USER
    PS1='HACK to avoid early-exit in .bashrc'
    . ~/.bashrc
    if [ -z "$ATMO_USER" ]; then
        echo 'Variable $ATMO_USER is not set in .bashrc! Abort!'
        exit 1 # 1 - ATMO_USER is not set!
    fi
    echo "Found user: $ATMO_USER"
}

set_directory ()
{
    # Set directory (via recursive `chown`)
    #TODO: Create a 'chown' line for each directory that should be re-assigned to the current user:
    #
  chown -R $ATMO_USER:iplant-everyone "/opt"
  exit 0
}

# This line will start the execution of the script
main
