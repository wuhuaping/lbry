from PyObjCTools import AppHelper
from twisted.internet.cfreactor import install
install(runner=AppHelper.runEventLoop)

from twisted.internet import reactor
from macos.LBRYApp import LBRYDaemonApp


def get_reactor():
    return reactor


def configure_app():
    app = LBRYDaemonApp.sharedApplication()
    reactor.addSystemEventTrigger("after", "shutdown", AppHelper.stopEventLoop)
