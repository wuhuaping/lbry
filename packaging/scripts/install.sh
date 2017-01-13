#!/bin/bash
#
# This script is used by travis to install lbry from source
#

set -o xtrace
set -e

source venv/bin/activate

pip install .

deactivate
