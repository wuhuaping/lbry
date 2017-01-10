import logging
import os
import sys
import threading
import webbrowser
from twisted.internet import reactor, error

try:
    import winxpgui as win32gui
except ImportError:
    import win32gui

from lbrynet import analytics
from lbrynet.core import log_support
from lbrynet.core import utils
from lbrynet.lbrynet_daemon import DaemonControl
from lbrynet.lbrynet_daemon.auth.client import LBRYAPIClient
from lbrynet import conf

from win32.LBRYWin32App import SysTrayIcon
from uri_handler import URIHandler

log = logging.getLogger(__name__)
utils.setup_certs_for_windows()


def get_reactor():
    return reactor


def configure_app():
    def LBRYApp():
        return SysTrayIcon(icon, hover_text, menu_options, on_quit=stop)

    def openui_(sender):
        webbrowser.open(conf.settings.UI_ADDRESS)

    def replyToApplicationShouldTerminate_():
        try:
            reactor.stop()
        except error.ReactorNotRunning:
            log.debug('Reactor already stopped')

    def stop(sysTrayIcon):
        replyToApplicationShouldTerminate_()

    if getattr(sys, 'frozen', False) and os.name == "nt":
        icon = os.path.join(os.path.dirname(sys.executable), conf.settings.ICON_PATH, 'lbry16.ico')
    else:
        icon = os.path.join(conf.settings.ICON_PATH, 'lbry16.ico')

    hover_text = conf.settings.APP_NAME
    menu_options = (('Open', icon, openui_),)

    if not utils.check_connection():
        log.warn('No Internet Connection')
        sys.exit(1)

    systray_thread = threading.Thread(target=LBRYApp)
    systray_thread.daemon = True
    systray_thread.start()

    DaemonControl.start_server_and_listen(
        launchui=True, use_auth=False,
        analytics_manager=analytics.Manager.new_instance()
    )


def main():
    utils.setup_certs_for_windows()
    conf.initialize_settings()
    conf.update_settings_from_file()

    log_file = conf.settings.get_log_filename()
    log_support.configure_logging(log_file, console=True)

    lbry_daemon = LBRYAPIClient.config()

    try:
        daemon_running = lbry_daemon.is_running()
        start_daemon = False
    except:
        start_daemon = True
    try:
        lbry_name = URIHandler.parse_name(sys.argv[1])
    except IndexError:
        lbry_name = None
    if start_daemon:
        reactor = get_reactor()
        reactor.run()
    else:
        URIHandler.open_address(lbry_name)


if __name__ == '__main__':
    main()