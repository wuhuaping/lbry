#!/bin/bash

source venv/bin/activate

sudo add-apt-repository -y ppa:spotify-jyrki/dh-virtualenv
sudo apt-get ${QUIET} update
sudo apt-get install -y --no-install-recommends software-properties-common
sudo apt-get install build-essential libffi-dev libssl-dev debhelper dh-virtualenv

WEB_UI_BRANCH="master"
SOURCE_DIR=$PWD

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [ -z ${TRAVIS+x} ]; then
  # if not on travis, its nice to see progress
  QUIET=""
else
    QUIET="-qq"
fi

BUILD_DIR="../lbry-build-$(date +%Y%m%d-%H%M%S)"

pip install git+https://github.com/jobevers/make-deb
pip install pip --upgrade
pip install setuptools --upgrade

# dpkg-buildpackage outputs its results into '..' so
# we need to move lbry into the build directory

(
    make-deb
    dpkg-buildpackage -us -uc
)

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
addfile "packaging/img/icons/lbry48.png" usr/share/icons/hicolor/48x48/apps/lbry.png
addfile "packaging/img/icons/lbry96.png" usr/share/icons/hicolor/96x96/apps/lbry.png
addfile "packaging/img/icons/lbry128.png" usr/share/icons/hicolor/128x128/apps/lbry.png
addfile "packaging/img/icons/lbry256.png" usr/share/icons/hicolor/256x256/apps/lbry.png
addfile "packaging/img/lbry.desktop" usr/share/applications/lbry.desktop

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
sudo chown -R root:root control data
tar -czf control.tar.gz -C control .
tar -cJf data.tar.xz -C data .
sudo chown root:root debian-binary control.tar.gz data.tar.xz
ar r "$PACKAGE" debian-binary control.tar.gz data.tar.xz

# TODO: we can append to data.tar instead of extracting it all and recompressing

if [[ ! -z "${TRAVIS_BUILD_DIR+x}" ]]; then
    # move it to a consistent place so that later it can be uploaded
    # to the github releases page
    mv "${PACKAGE}" "${TRAVIS_BUILD_DIR}/${PACKAGE}"
    # want to be able to check the size of the result in the log
    ls -l "${TRAVIS_BUILD_DIR}/${PACKAGE}"
fi

deactivate nondestructive
