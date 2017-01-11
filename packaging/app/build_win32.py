import os
import sys
import opcode
from cx_Freeze import Executable
from cx_Freeze import setup
from pip import req as pip_req, download as pip_download
import requests.certs
import site
import pkg_resources
from lbrynet import __version__ as lbrynet_version


app_dir = os.path.join("packaging", "app")
daemon_dir = os.path.join('lbrynet', 'lbrynet_daemon')
icon_dir = os.path.join("packaging", "img")
win_icon = os.path.join(icon_dir, "lbry256.ico")
wordlist_path = pkg_resources.resource_filename('lbryum', 'wordlist')

# Allow virtualenv to find distutils of base python installation
distutils_path = os.path.join(os.path.dirname(opcode.__file__), 'distutils')

schemas = os.path.join(site.getsitepackages()[1], "jsonschema", "schemas")
onlyfiles = [f for f in os.listdir(schemas) if os.path.isfile(os.path.join(schemas, f))]
zipincludes = [(os.path.join(schemas, f), os.path.join("jsonschema", "schemas", f)) for f in onlyfiles]


def package_files(directory):
    for path, _, filenames in os.walk(directory):
        for filename in filenames:
            yield os.path.join('..', path, filename)


module_names = {
    'Twisted': 'twisted',
    'dnspython': 'dns',
    'loggly-python-handler': 'loggly',
    'pyyaml': 'yaml',
    'protobuf': 'google.protobuf',
    'slowaes': 'aes',
    'txJSON-RPC': 'txjsonrpc',
    'pycryptodome': 'Crypto',
    'pypiwin32': 'win32api'
}


def get_module_name(m_name):
    if m_name not in module_names:
        return m_name
    return module_names[m_name]


def get_req(req):
    for c in ['==', '<=', '>=']:
        if c in req:
            r, v = req.split(c)
            return get_module_name(r)
    return get_module_name(req)


def get_requirements():
    reqs = []
    requirements = pip_req.parse_requirements('requirements.txt', session=pip_download.PipSession())

    for item in requirements:
        if item.req:
            reqs.append(get_req(str(item.req)))
        if getattr(item, 'markers', None):
            if item.markers is not None:
                # remove OS specific requirements
                if getattr(item.markers, 'evaluate', None):
                    if not item.markers.evaluate():
                        reqs.remove(get_req(str(item.req)))
                else:
                    print "Don't know how to process markers: %s" % str(item.markers)
    return reqs


def get_windows_executables(dist_name):
    tray_app = Executable(
        script=os.path.join(app_dir, 'main.py'),
        base='Win32GUI',
        icon=win_icon,
        targetName='{0}.exe'.format(dist_name)
    )

    daemon_exe = Executable(
        script=os.path.join(daemon_dir, 'DaemonControl.py'),
        icon=win_icon,
        targetName='lbrynet-daemon.exe'
    )

    cli_exe = Executable(
        script=os.path.join(daemon_dir, 'DaemonCLI.py'),
        icon=win_icon,
        targetName='lbrynet-cli.exe'
    )
    return tray_app, daemon_exe, cli_exe


def get_windows_options(requires, dist_name):
    options = {
        'build_exe': {
            'include_msvcr': True,
            'includes': [],
            'packages': requires,
            'excludes': ['distutils', 'collections.sys', 'collections._weakref', 'collections.abc',
                         'Tkinter', 'tk', 'tcl', 'PyQt4', 'nose', 'mock'
                                                                  'zope.interface._zope_interface_coptimizations',
                         'leveldb'],
            'include_files': [(distutils_path, 'distutils'), (requests.certs.where(), 'cacert.pem'),
                              (os.path.join(icon_dir, 'lbry16.ico'), os.path.join(icon_dir, 'lbry16.ico')),
                              (os.path.join(icon_dir, 'lbry256.ico'), os.path.join(icon_dir, 'lbry256.ico')),
                              (os.path.join(wordlist_path, 'chinese_simplified.txt'),
                               os.path.join('wordlist', 'chinese_simplified.txt')),
                              (os.path.join(wordlist_path, 'english.txt'), os.path.join('wordlist', 'english.txt')),
                              (os.path.join(wordlist_path, 'japanese.txt'),
                               os.path.join('wordlist', 'japanese.txt')),
                              (os.path.join(wordlist_path, 'portuguese.txt'),
                               os.path.join('wordlist', 'portuguese.txt')),
                              (os.path.join(wordlist_path, 'spanish.txt'), os.path.join('wordlist', 'spanish.txt'))
                              ],
            'namespace_packages': ['zope', 'google'],
            "zip_includes": zipincludes
        },
        'bdist_msi': {
            'upgrade_code': '{18c0e933-ad08-44e8-a413-1d0ed624c100}',
            'add_to_path': True,
            # Default install path is 'C:\Program Files\' for 32-bit or 'C:\Program Files (x86)\' for 64-bit
            # 'initial_target_dir': r'[LocalAppDataFolder]\{0}'.format(name),
            'data': {
                "Shortcut": [
                    get_win_shortcut_params(dist_name, 'LBRYShortcut', directory='DesktopFolder'),
                    get_win_shortcut_params(dist_name, 'ProgramMenuLBRYShortcut', directory='ProgramMenuFolder'),
                ]
            }
        }
    }
    return options


def find_data_file(filename):
    if getattr(sys, 'frozen', False):
        # The application is frozen
        data_dir = os.path.dirname(sys.executable)
    else:
        # The application is not frozen
        # Change this bit to match where you store your data files:
        data_dir = os.path.dirname(__file__)
    return os.path.join(data_dir, filename)


def get_win_shortcut_params(dist_name, shortcut, directory=None, target=None, name=None, component=None, app_args=None,
                            description=None, hotkey=None, icon=None, icon_index=None, show_command=None, wkdir=None):
    params = (
        shortcut,
        directory or 'ProgramMenuFolder',
        name or 'LBRY',
        component or 'TARGETDIR',
        target or '[TARGETDIR]\{0}.exe'.format(dist_name),
        app_args,
        description,
        hotkey,
        icon,
        icon_index,
        show_command,
        wkdir or 'TARGETDIR',
    )
    return params


name = "LBRY"
data_files = [os.path.join('packaging', 'img', 'app.icns')]
dist_name = "LBRY"
description = "A decentralized media library and marketplace"
author = "LBRY, Inc"
url = "lbry.io"
maintainer = "Jack Robison"
maintainer_email = "jack@lbry.io"
keywords = "LBRY"
requires = get_requirements()
exes = get_windows_executables(name)
options = get_windows_options(requires, name)

setup(
    name=name,
    description=description,
    version=lbrynet_version,
    url=url,
    author=author,
    keywords=keywords,
    data_files=data_files,
    options=options,
    executables=exes,
)