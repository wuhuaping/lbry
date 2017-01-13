#!/bin/bash

set -o xtrace

set +u
source venv/bin/activate
set -u

# TODO: would be nice to get rid of unqlite and cython.  They are only used for
#       ptcwallet related bits.
pip install Cython
pip install unqlite
pip install mock
pip install coveralls

# have to do `which trial` instead of simply trial because coverage needs the full path
PYTHONPATH=. coverage run --source=lbrynet `which trial` tests
coveralls

set +eu
deactivate nondestructive
