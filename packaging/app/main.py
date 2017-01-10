import sys

LINUX = 'linux'
DARWIN = 'darwin'
WINDOWS = 'win32'

if sys.platform.startswith("darwin"):
    platform = DARWIN
    from main_macos import get_reactor, configure_app
elif sys.platform.startswith("win"):
    platform = WINDOWS
    from main_win32 import get_reactor, configure_app
else:
    raise Exception("Unknown os: %s" % sys.platform)

from lbrynet.core import log_support
from lbrynet import conf
from lbrynet.lbrynet_daemon.auth.client import LBRYAPIClient
from urllib2 import URLError
from uri_handler import URIHandler

conf.initialize_settings()
conf.update_settings_from_file()
log_file = conf.settings.get_log_filename()
log_support.configure_logging(log_file, console=True)


def main():
    need_start = False
    lbry_daemon = LBRYAPIClient.config()
    try:
        daemon_running = lbry_daemon.is_running()
        from twisted.internet import reactor
    except URLError:
        need_start = True
        reactor = get_reactor()
        configure_app()
    try:
        lbry_name = URIHandler.parse_name(sys.argv[1])
        log_file.info("Rendering URI: %s", lbry_name)
        URIHandler.open_address(lbry_name)
    except IndexError:
        pass
    if need_start:
        reactor.run()


if __name__ == "__main__":
    main()