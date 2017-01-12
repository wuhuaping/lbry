#!/bin/bash
#
# This script is used by travis to install lbry from source
#

source venv/bin/activate

pip install .

deactivate