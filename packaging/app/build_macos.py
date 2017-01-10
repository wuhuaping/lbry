from setuptools import setup
from pip import req as pip_req, download as pip_download
import os
from lbrynet.conf import PROTOCOL_PREFIX, APP_NAME

APP_DIR = os.path.join("packaging", "app")
APP_PATH = os.path.join(APP_DIR, "main.py")
DATA_FILES = [os.path.join('packaging', 'img', 'app.icns')]

requirements_path = os.path.join(APP_DIR, "macos_requirements.txt")
_requirements = pip_req.parse_requirements(requirements_path, session=pip_download.PipSession())
requirements = []
for item in _requirements:
    if item.req:
        requirements.append(str(item.req))
    if getattr(item, 'markers', None):
        if item.markers is not None:
            # remove OS specific requirements
            if getattr(item.markers, 'evaluate', None):
                if not item.markers.evaluate():
                    requirements.remove(str(item.req))
            else:
                print "Don't know how to process markers: %s" % str(item.markers)

OPTIONS = {
    'iconfile': os.path.join('packaging', 'img', 'app.icns'),
    'plist': {
        'CFBundleIdentifier': 'io.lbry.LBRY',
        'LSUIElement': True,
        'CFBundleURLTypes': [
                    {
                    'CFBundleURLTypes': 'LBRY',
                    'CFBundleURLSchemes': [PROTOCOL_PREFIX]
                    }
        ]
    },
    'includes': ['zope.interface', 'PyObjCTools'],
    'packages': requirements,
}

setup(
    name=APP_NAME,
    app=[APP_PATH],
    options={'py2app': OPTIONS},
    data_files=DATA_FILES,
    setup_requires=['py2app'],
)
