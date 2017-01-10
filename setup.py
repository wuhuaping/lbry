#!/usr/bin/env python

import sys
import os
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup, find_packages
from pip import req as pip_req, download as pip_download
from lbrynet import __version__

LINUX = 'linux'
DARWIN = 'darwin'
WINDOWS = 'win32'

if sys.platform.startswith("linux"):
    platform = LINUX
elif sys.platform.startswith("darwin"):
    platform = DARWIN
elif sys.platform.startswith("win"):
    platform = WINDOWS
else:
    raise Exception("Unknown os: %s" % sys.platform)


def package_files(directory):
    for path, _, filenames in os.walk(directory):
        for filename in filenames:
            yield os.path.join('..', path, filename)


def get_requirements():
    reqs = []
    requirements = pip_req.parse_requirements('requirements.txt', session=pip_download.PipSession())

    for item in requirements:
        if item.req:
            reqs.append(str(item.req))
        if getattr(item, 'markers', None):
            if item.markers is not None:
                # remove OS specific requirements
                if getattr(item.markers, 'evaluate', None):
                    if not item.markers.evaluate():
                        reqs.remove(str(item.req))
                else:
                    print "Don't know how to process markers: %s" % str(item.markers)

    return reqs


# TODO: fix miniupnpc on appveyor

base_dir = os.path.abspath(os.path.dirname(__file__))
package_name = "lbrynet"
dist_name = "LBRY"
description = "A decentralized media library and marketplace"
author = "LBRY, Inc"
url = "lbry.io"
maintainer = "Jack Robison"
maintainer_email = "jack@lbry.io"
keywords = "LBRY"
console_scripts = [
    'lbrynet-daemon = lbrynet.lbrynet_daemon.DaemonControl:start',
    'stop-lbrynet-daemon = lbrynet.lbrynet_daemon.DaemonControl:stop',
    'lbrynet-cli = lbrynet.lbrynet_daemon.DaemonCLI:main'
]
package_data = {package_name: list(package_files('lbrynet/resources/ui'))}
entry_points = {'console_scripts': console_scripts}
requires = get_requirements()

if platform == DARWIN:
    os.environ['CFLAGS'] = '-I/usr/local/opt/openssl/include'

setup(name=package_name,
      description=description,
      version=__version__,
      maintainer=maintainer,
      maintainer_email=maintainer_email,
      url=url,
      author=author,
      keywords=keywords,
      packages=find_packages(base_dir),
      install_requires=requires,
      entry_points=entry_points,
      package_data=package_data,
      # If this is True, setuptools tries to build an egg
      # and py2app / modulegraph / imp.find_module
      # doesn't like that.
      zip_safe=False)