#!/bin/bash

set -o xtrace
set -eu

# Install and update pip, set up venv, and install brew/apt-get required stuff
#
if [ ${TRAVIS_OS_NAME} = "linux" ]; then
    SUDO=''
    if (( $EUID != 0 )); then
        SUDO='sudo'
    fi

    if [ -z ${TRAVIS+x} ]; then
      # if not on travis, its nice to see progress
      QUIET=""
    else
        QUIET="-qq"
    fi

    # get the required OS packages
    $SUDO apt-get ${QUIET} update
    $SUDO apt-get ${QUIET} install -y --no-install-recommends \
          build-essential python-dev libffi-dev libssl-dev git \
          libgmp3-dev wget ca-certificates python-virtualenv \
	  software-properties-common 
else
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
fi

# Configure build-specific things
#
# changes to this script also need to be added to build.ps1 for windows
add_ui() {
    wget https://s3.amazonaws.com/lbry-ui/development/dist.zip -O dist.zip
    unzip -oq dist.zip -d lbrynet/resources/ui
    wget https://s3.amazonaws.com/lbry-ui/development/data.json -O lbrynet/resources/ui/data.json
}

set_build() {
  local file="lbrynet/build_type.py"
  # cannot use 'sed -i' because BSD sed and GNU sed are incompatible
  sed 's/^\(BUILD = "\)[^"]\+\(".*\)$/\1'"${1}"'\2/' "$file" > tmpbuildfile
  mv -- tmpbuildfile "$file"
}

# create a virtualenv so we don't muck with anything on the system
virtualenv venv

# need to unset these or else we can't activate
set +u
source venv/bin/activate
set -u

pip install pip --upgrade
pip install requests[security]

# install lbrynet reqs
pip install -r requirements.txt

IS_RC_REGEX="v[[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+rc[[:digit:]]+"

if [[ -z "$TRAVIS_TAG" ]]; then
    python packaging/scripts/append_sha_to_version.py lbrynet/__init__.py "${TRAVIS_COMMIT}"
    add_ui
    set_build "qa"
elif [[ "$TRAVIS_TAG" =~ $IS_RC_REGEX ]]; then
    # If the tag looks like v0.7.6rc0 then this is a tagged release candidate.
    add_ui
    set_build "rc"
else
    set_build "release"
fi

# need to unset these or else we can't deactivate
set +eu
deactivate
