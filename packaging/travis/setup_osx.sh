#!/bin/sh

set -euo pipefail
set -o xtrace

# Need to update to 2.7.13 because http://bugs.python.org/issue28440
wget https://www.python.org/ftp/python/2.7.13/python-2.7.13-macosx10.6.pkg
sudo installer -pkg python-2.7.13-macosx10.6.pkg -target /
pip install -U pip
brew update
brew install openssl
brew link --force openssl
