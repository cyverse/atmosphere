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
# current requirements.

PIP_TOOLS_VERSION=1.11.0

function main {

    # Ensure that pip-tools is installed
    which pip-compile &>/dev/null;
    if [[ $? -ne 0 ]]; then
        warn_missing_pip_tools;
        exit 1;
    fi;

    # Ensure the proper version of pip-tools
    if [[ $(pip-tools-version) != $PIP_TOOLS_VERSION ]]; then
        warn_improper_pip_tools_version;
        exit 1;
    fi;

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
    pip-compile --max-rounds 20 --dry-run -o requirements.txt requirements.in 2>/dev/null;
}

function pip-tools-version {
    pip-compile --version | grep -Po '\d+\.\d+\.\d+';
}

function warn_improper_pip_tools_version {
    warn "pip-tools is the wrong version." >&2;
    echo "To install run: pip install pip-tools==$PIP_TOOLS_VERSION" >&2;
}

function warn_missing_pip_tools {
    warn "pip-tools is missing." >&2;
    echo "To install run: pip install pip-tools==$PIP_TOOLS_VERSION" >&2;
}

function warn_bad_requirements {
    warn "requirements.txt was not generated properly!" >&2;
    echo "This likely means the author didn't edit the requirements.in file!" >&2;
    echo "See REQUIREMENTS.md" >&2;
}

function generate_dev_requirements {
    pip-compile --dry-run -o dev_requirements.txt \
        dev_requirements.in requirements.txt 2>/dev/null;
}

function warn_bad_dev_requirements {
    warn "dev_requirements.txt was not generated properly!" >&2;
    echo "This file must be generated after requirements.txt is generated," \
         "because it uses that file as an input." >&2;
    echo "See REQUIREMENTS.md" >&2;
}

function warn_bad_dev_requirements {
    warn "dev_requirements.txt was not generated properly!" >&2;
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

function warn {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "$@";
    printf "${default}";
}

main
