#!/bin/bash

set -o errexit
set -o xtrace

# Install stuff needed to build the app
set +u
source venv/bin/activate
set -u

if [ ${TRAVIS_OS_NAME} = "osx" ]; then
    # Clone and install pyobjc 3.2.1 w/ supportsSecureCoding patch (Sierra support)
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
else
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

    $SUDO apt-get install -y --no-install-recommends software-properties-common
    $SUDO add-apt-repository -y ppa:spotify-jyrki/dh-virtualenv
    $SUDO apt-get ${QUIET} update
    $SUDO apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev debhelper dh-virtualenv

    WEB_UI_BRANCH="master"
    SOURCE_DIR=$PWD
    BUILD_DIR="../lbry-build-$(date +%Y%m%d-%H%M%S)"

    mkdir -p "$BUILD_DIR"
    # cd "$BUILD_DIR"

    # TODO: explain why this is patched
    # TOD: move this out of jobevers and into lbryio
    pip install git+https://github.com/jobevers/make-deb

    # dpkg-buildpackage outputs its results into '..' so
    # we need to move lbry into the build directory

    make-deb
    dpkg-buildpackage -us -uc

    ### insert our extra files

    # extract .deb
    PACKAGE="$(ls | grep '.deb')"
    ar vx "$PACKAGE"
    mkdir -p control data
    tar -xzf control.tar.gz --directory control

    # The output of the travis build is a
    # tar.gz and the output locally is tar.xz.
    # Instead of having tar detect the compression used, we
    # could update the config to output the same in either spot.
    # Unfortunately, doing so requires editting some auto-generated
    # files: http://linux.spiney.org/forcing_gzip_compression_when_building_debian_packages
    tar -xf data.tar.?z --directory data

    PACKAGING_DIR='lbry/packaging/app/ubuntu'

    # set web ui branch
    sed -i "s/^WEB_UI_BRANCH='[^']\+'/WEB_UI_BRANCH='$WEB_UI_BRANCH'/" "$PACKAGING_DIR/lbry"

    # add files
    function addfile() {
      FILE="$1"
      TARGET="$2"
      mkdir -p "$(dirname "data/$TARGET")"
      cp -d "$FILE" "data/$TARGET"
      echo "$(md5sum "data/$TARGET" | cut -d' ' -f1)  $TARGET" >> control/md5sums
    }

    function addlink() {
      SRC="$1"
      TARGET="$2"
      TMP="$PACKAGING_DIR/lbry-temp-symlink"
      ln -s "$SRC" "$TMP"
      addfile "$TMP" "$TARGET"
      rm "$TMP"
    }

    # add icons
    addfile "packaging/img/lbry32.png" usr/share/icons/hicolor/32x32/apps/lbry.png
    addfile "packaging/img/lbry48.png" usr/share/icons/hicolor/48x48/apps/lbry.png
    addfile "packaging/img/lbry96.png" usr/share/icons/hicolor/96x96/apps/lbry.png
    addfile "packaging/img/lbry128.png" usr/share/icons/hicolor/128x128/apps/lbry.png
    addfile "packaging/img/lbry256.png" usr/share/icons/hicolor/256x256/apps/lbry.png
    addfile "packaging/app/ubuntu/lbry.desktop" usr/share/applications/lbry.desktop

    # add lbry executable script
    BINPATH=usr/share/python/lbrynet/bin
    addfile "$PACKAGING_DIR/lbry" "$BINPATH/lbry"

    # symlink scripts into /usr/bin
    for script in "lbry" "lbrynet-daemon" "lbrynet-cli" "stop-lbrynet-daemon"; do
      addlink "/$BINPATH/$script" "usr/bin/$script"
    done

    # add postinstall script
    cat "$PACKAGING_DIR/postinst_append" >> control/postinst

    # change package name from lbrynet to lbry
    sed -i 's/^Package: lbrynet/Package: lbry/' control/control
    echo "Conflicts: lbrynet (<< 0.3.5)" >> control/control
    echo "Replaces: lbrynet (<< 0.3.5)" >> control/control

    # repackage .deb
    $SUDO chown -R root:root control data
    tar -czf control.tar.gz -C control .
    tar -cJf data.tar.xz -C data .
    $SUDO chown root:root debian-binary control.tar.gz data.tar.xz
    ar r "$PACKAGE" debian-binary control.tar.gz data.tar.xz

    # TODO: we can append to data.tar instead of extracting it all and recompressing

    if [[ ! -z "${TRAVIS_BUILD_DIR+x}" ]]; then
        # move it to a consistent place so that later it can be uploaded
        # to the github releases page
        mv "${PACKAGE}" "${TRAVIS_BUILD_DIR}/${PACKAGE}"
        # want to be able to check the size of the result in the log
        ls -l "${TRAVIS_BUILD_DIR}/${PACKAGE}"
    fi
fi

deactivate
