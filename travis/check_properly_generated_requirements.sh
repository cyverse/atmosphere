#!/bin/bash

#
# This scripts ensures that requirements files were generated based on the
# instructions found in ../REQUIREMENTS.md
#
#   pip-compile -o requirements.txt requirements.in
#   pip-compile -o dev_requirements.txt  dev_requirements.in requirements.txt
#
# Notes:
# This script properly generates the requirements and performs a diff with the
# current requirements. There is some noise but thats basically it. This
# script tries to be pretty quiet, if you're debugging you should remove the
# silencing file redirections.

function main {

    # Ensure that requirements.txt was generated properly
    diff <(generate_requirements | normalize) <(normalize < requirements.txt);

    # If the expected didn't meet the actual
    if [[ $? -ne 0 ]]; then
        warn_bad_requirements;
        exit 1;
    fi;

    # Ensure that dev_requirements.txt was generated properly
    diff <(generate_dev_requirements | normalize) <(normalize < dev_requirements.txt);

    # If the expected didn't meet the actual
    if [[ $? -ne 0 ]]; then
        warn_bad_dev_requirements;
        exit 1;
    fi;

    echo_success_message;
}

# Normalize a requirements stream to just names and versions
function normalize {
    # Convert to lowercase, strip out whitespace and comments
    tr [:upper:] [:lower:] | grep -oP '^[^ #]*'
}

function generate_requirements {
    pip-compile --dry-run -o requirements.txt requirements.in 2>/dev/null;
}

function warn_bad_requirements {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "requirements.txt was not generated properly!" >&2;
    printf "${default}";
    echo "This likely means the author didn't edit the requirements.in file!" >&2;
    echo "See REQUIREMENTS.md" >&2;
}

function generate_dev_requirements {
    pip-compile --dry-run -o dev_requirements.txt \
        dev_requirements.in requirements.txt 2>/dev/null;
}

function warn_bad_dev_requirements {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "dev_requirements.txt was not generated properly!" >&2;
    printf "${default}";
    echo "This file must be generated after requirements.txt is generated," \
         "because it uses that file as an input." >&2;
    echo "See REQUIREMENTS.md" >&2;
}

function warn_bad_dev_requirements {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "dev_requirements.txt was not generated properly!" >&2;
    printf "${default}";
    echo "This file must be generated after requirements.txt is generated," \
         "because it uses that file as an input." >&2;
    echo "See REQUIREMENTS.md" >&2;
}

function echo_success_message {
    local default="\e[0m" green="\e[32m";
    printf "${green}";
    echo "requirements.txt and dev_requirements.txt passed the test!" >&2;
    printf "${default}";
}

main
