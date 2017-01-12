#!/bin/bash
#
# This script is used by travis to install lbry from source
#

set -euo pipefail
set -o xtrace

if [ `uname` = "Linux" ]; then
    source venv/bin/activate
fi

pip install -r requirements.txt
pip install .

if [ `uname` = "Linux" ]; then
    deactivate nondestructive
fi