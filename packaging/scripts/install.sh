#!/bin/bash
#
# This script is used by travis to install lbry from source
#

if [ `uname` = "Linux" ]; then
    source venv/bin/activate
fi

pip install .

if [ `uname` = "Linux" ]; then
    deactivate nondestructive
fi