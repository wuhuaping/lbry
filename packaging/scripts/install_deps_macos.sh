#!/bin/sh

set -euo pipefail
set -o xtrace

brew update

# follow this pattern to avoid failing if its already
# installed by brew:
# http://stackoverflow.com/a/20802425
if brew ls --versions gmp > /dev/null; then
    echo 'gmp is already installed by brew'
else
    brew install gmp
fi

if brew ls --versions openssl > /dev/null; then
    echo 'openssl is already installed by brew'
else
    brew install openssl
    brew link --force openssl
fi


if brew ls --versions hg > /dev/null; then
    echo 'hg is already installed by brew'
else
    brew install hg
fi

if brew ls --versions wget > /dev/null; then
    echo 'wget is already installed by brew'
else
    brew install wget
fi

if [ ${ON_TRAVIS} = true ]; then
    wget https://www.python.org/ftp/python/2.7.11/python-2.7.11-macosx10.6.pkg
    sudo installer -pkg python-2.7.11-macosx10.6.pkg -target /
    pip install -U pip
    pip install pip --upgrade
    pip install setuptools --upgrade
fi

# pyopenssl is needed because OSX ships an old version of openssl by default
# and python will use it without pyopenssl
pip install PyOpenSSL
pip install jsonrpc
pip install certifi

pip install -r requirements.txt
