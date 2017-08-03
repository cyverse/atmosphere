#!/bin/bash

#
# Print all files that changed in this travis pr
#

# Note:
# $TRAVIS_COMMIT_RANGE is not defined if a project has a single commit. That
# will just result in empty output here which is desired.
git diff --name-only --diff-filter=M $TRAVIS_COMMIT_RANGE --;
