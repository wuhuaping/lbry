import os
import sys
import opcode
from cx_Freeze import Executable
from cx_Freeze import setup as cx_setup
import requests.certs
import site
import pkg_resources


app_dir = os.path.join("packaging", "tray_app", "win32")
daemon_dir = os.path.join('lbrynet', 'lbrynet_daemon')
icon_dir = os.path.join("packaging", "img")
win_icon = os.path.join(icon_dir, "lbry256.ico")
wordlist_path = pkg_resources.resource_filename('lbryum', 'wordlist')

# Allow virtualenv to find distutils of base python installation
distutils_path = os.path.join(os.path.dirname(opcode.__file__), 'distutils')

schemas = os.path.join(site.getsitepackages()[1], "jsonschema", "schemas")
onlyfiles = [f for f in os.listdir(schemas) if os.path.isfile(os.path.join(schemas, f))]
zipincludes = [(os.path.join(schemas, f), os.path.join("jsonschema", "schemas", f)) for f in onlyfiles]


def get_windows_executables(dist_name):
    tray_app = Executable(
        script=os.path.join(app_dir, 'LBRYWin32App.py'),
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
                            description=None, hotkey=None, icon=None, icon_index=None, wkdir=None):
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
        wkdir or 'TARGETDIR',
    )
    return params


def setup(requires, name, platform, description, version, maintainer, maintainer_email, url, author,
          keywords, base_dir, entry_points, package_data, dependency_links, data_files):

    exes = get_windows_executables(name)
    options = get_windows_options(requires, name)

    cx_setup(
        name=name,
        description=description,
        version=version,
        maintainer=maintainer,
        maintainer_email=maintainer_email,
        url=url,
        author=author,
        keywords=keywords,
        data_files=data_files,
        options=options,
        executables=exes,
        package_data=package_data
    )