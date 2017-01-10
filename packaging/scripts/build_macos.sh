#!/bin/bash

set -o errexit
set -o xtrace

# Install stuff needed to build the app

# to make pyobjc wheels:
#    hg clone https://bitbucket.org/jackrobison/pyobjc
#    cd pyobjc
#    python development-support/set-pyobjc-version 3.2.1
#    pip wheel pyobjc-framework-*
#    pip wheel pyobjc-core
#    pip wheel pyobjc


hg clone https://bitbucket.org/jackrobison/pyobjc
cd pyobjc
python development-support/set-pyobjc-version 3.2.1
pip install ./pyobjc-core --upgrade
pip install ./pyobjc-framework-Cocoa --upgrade
pip install ./pyobjc-framework-CFNetwork --upgrade
pip install ./pyobjc-framework-Quartz --upgrade
pip install ./pyobjc-framework-NotificationCenter --upgrade
cd ..
rm -rf pyobjc

#    mkdir -p wheels
#    cd wheels
#    wget https://s3.amazonaws.com/files.lbry.io/wheels.zip
#    unzip wheels.zip
#    rm wheels.zip
#
#    pip install ./pyobjc_framework_Cocoa-3.2.1-cp27-cp27m-macosx_10_6_intel.whl --upgrade
#    pip install ./pyobjc_framework_CFNetwork-3.2.1-cp27-cp27m-macosx_10_6_intel.whl --upgrade
#    pip install ./pyobjc_framework_Quartz-3.2.1-cp27-cp27m-macosx_10_6_intel.whl --upgrade
#    pip install ./pyobjc_core-3.2.1-cp27-cp27m-macosx_10_6_intel.whl --upgrade
#    pip install ./pyobjc-3.2.1-cp27-none-any.whl --upgrade
#    cd ..
#    rm -rf wheels
#fi

pip install modulegraph==0.13
pip install hg+https://bitbucket.org/jackrobison/py2app
pip install wheel
pip install dmgbuild==1.1.0

# Build

DEST=`pwd`
tmp="${DEST}/build"

rm -rf build dist LBRY.app

if [ ${ON_TRAVIS} = true ]; then
    export PATH=${PATH}:/Library/Frameworks/Python.framework/Versions/2.7/bin
fi

NAME=`python setup.py --name`
VERSION=`python setup.py -V`

if [ -z ${SKIP_PYLINT+x} ]; then
    ./packaging/scripts/run_pylint.sh packaging/app/macos/
fi

# py2app will skip _cffi_backend without explicitly including it
# and without this, we will get SSL handshake errors when connecting
# to bittrex
python packaging/app/build_macos.py py2app -i _cffi_backend

echo "Removing i386 libraries"

remove_arch () {
    if [[ `lipo "$2" -verify_arch "$1"` ]]; then
       lipo -output build/lipo.tmp -remove "$1" "$2" && mv build/lipo.tmp "$2"
    fi
}

for i in `find dist/LBRY.app/Contents/Resources/lib/python2.7/lib-dynload/ -name "*.so"`; do
    remove_arch i386 $i
done

if [ ${SKIP_SIGN} = false ]; then
    echo "Signing LBRY.app"
    codesign -s "${LBRY_DEVELOPER_ID}" -f "${DEST}/dist/LBRY.app/Contents/Frameworks/Python.framework/Versions/2.7"
    codesign -s "${LBRY_DEVELOPER_ID}" -f "${DEST}/dist/LBRY.app/Contents/Frameworks/libgmp.10.dylib"
    codesign -s "${LBRY_DEVELOPER_ID}" -f "${DEST}/dist/LBRY.app/Contents/MacOS/python"
    # adding deep here as well because of subcomponent issues
    codesign --deep -s "${LBRY_DEVELOPER_ID}" -f "${DEST}/dist/LBRY.app/Contents/MacOS/LBRY"
    codesign -vvvv "${DEST}/dist/LBRY.app"
fi

rm -rf $tmp
mv dist/LBRY.app LBRY.app

rm -rf dist "${NAME}.${VERSION}.dmg"
dmgbuild -s ./packaging/scripts/dmg_settings.py "LBRY" "${NAME}.${VERSION}.dmg"
