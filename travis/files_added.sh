#!/bin/bash

#
# Print all files that were added in this travis pr
#

if [[ -z "$TRAVIS_COMMIT_RANGE" ]]; then
   # If a project has a single commit, treat all files as added!
   git ls-files;
else
   git diff --name-only --diff-filter=A $TRAVIS_COMMIT_RANGE --;
fi
