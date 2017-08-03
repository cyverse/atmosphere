#!/bin/bash

#
# This script runs prospector-the static code linter-on changed files.
#
# Notes:
# Introducing linting into a project can be tricky. This script runs a strict
# variant on newly added files, and a lenient variant on modified files. This
# is a share-the-pain approach to raising the quality of the project.

function main {
    local python_added=$(
        ./travis/files_added.sh | grep '\.py$'
    );
    local python_changed=$(
        ./travis/files_changed.sh | grep '\.py$'
    );

    # If some python files were added
    if [[ -n "$python_added" ]]; then

        lint_strict $python_added;

        # Files changed didn't pass the strict test
        if [[ $? == 1 ]]; then
            strict_err;
            exit 1;
        fi
    fi;

    # If some python files were changed
    if [[ -n "$python_changed" ]]; then

        lint_lenient $python_changed;

        # Files changed didn't pass the lenient test
        if [[ $? == 1 ]]; then
            lenient_err;
            exit 1;
        fi
    fi;

    echo_success_message;
}

function strict_err {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "The strict linter failed!" >&2;
    printf "${default}";
    echo "Note: the strict linter is run only on newly added files." >&2;
}

function lenient_err {
    local default="\e[0m" red="\e[31m";
    printf "${red}";
    echo "The lenient linter failed!" >&2;
    printf "${default}";
    echo "Note: the lenient linter is run only on files that changed. This" \
         "means that you may have to clean up files where you only made a small" \
         "change." >&2;
}

function lint_strict {
    prospector $@;
}

function lint_lenient {
    prospector --strictness verylow $@;
}

function echo_success_message {
    local default="\e[0m" green="\e[32m";
    printf "${green}";
    echo "Codebase passed the linter!" >&2;
    printf "${default}";
}

main $@;
