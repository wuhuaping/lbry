from lbrynet.core import log_support

import argparse
import logging
import functools
import os
import sys

import appdirs
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import endpoints
from twisted.python import log

from lbrynet.lbryfile.client import EncryptedFileOptions
from lbrynet.lbryfile import EncryptedFileMetadataManager
from lbrynet.lbryfile.client import EncryptedFileDownloader
from lbrynet.lbrynet_daemon import Downloader
from lbrynet.lbryfilemanager import EncryptedFileManager
from lbrynet.core import Session
from lbrynet.core import utils
from lbrynet.core import Wallet
from lbrynet.core import StreamDescriptor
from lbrynet.lbryfile import StreamDescriptor as StreamDescriptor
from lbrynet import conf

logger = logging.getLogger()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    args = parser.parse_args()

    log_support.configure_console()

    db_dir = appdirs.user_data_dir('LBRY')
    lbrycrd = appdirs.user_data_dir('lbrycrd')
    # lets download to the current directory
    download_directory = os.getcwd()

    wallet = LBRYWallet.LBRYcrdWallet(db_dir, wallet_conf=os.path.join(lbrycrd, 'lbrycrd.conf'))
    session = Session.LBRYSession(
        conf.MIN_BLOB_DATA_PAYMENT_RATE,
        db_dir=db_dir,
        lbryid=utils.generate_id(),
        blob_dir=os.path.join(db_dir, 'blobfiles'),
        dht_node_port=4444,
        known_dht_nodes=conf.KNOWN_DHT_NODES,
        peer_port=3333,
        use_upnp=False,
        wallet=wallet
    )
    sd_identifier = setup_sd_identifier(session, download_directory)
    lbry_file_metadata_manager = LBRYFileMetadataManager.DBLBRYFileMetadataManager(db_dir)
    lbry_file_manager = LBRYFileManager.LBRYFileManager(
        session,
        lbry_file_metadata_manager,
        sd_identifier,
        download_directory=download_directory
    )
    get_stream = LBRYDownloader.GetStream(
        sd_identifier,
        session,
        wallet,
        lbry_file_manager,
        max_key_fee=conf.DEFAULT_MAX_KEY_FEE,
        data_rate=conf.MIN_BLOB_DATA_PAYMENT_RATE,
        timeout=conf.DEFAULT_TIMEOUT,
        download_directory=download_directory
    )

    d = session.setup()
    d.addCallback(eatarg(lbry_file_metadata_manager.setup))
    d.addCallback(eatarg(lbry_file_manager.setup))
    d.addCallback(eatarg(print_balance, wallet))
    d.addCallback(eatarg(print_stream_info, wallet, args.name))
    d.addCallback(functools.partial(download_stream, get_stream, args.name))
    d.addCallback(functools.partial(wait_until_done, get_stream))
    d.addCallback(eatarg(reactor.stop))
    d.addErrback(log_and_stop)
    logger.info('Starting reactor')
    reactor.run()

    # This set of callback can be used to look at the metadata (like filename, size)
    #
    # d.addCallback(functools.partial(download_stream_identifier, session))
    # d.addCallback(sd_identifier.get_metadata_for_sd_blob)
    # d.addCallback(lambda metadata: metadata.validator.info_to_show())
    # d.addCallback(functools.partial(print_, 'metadata:'))


def sleep(seconds):
    d = defer.Deferred()
    reactor.callLater(seconds, d.callback, seconds)
    return d


@defer.inlineCallbacks
def wait_until_done(get_stream, args):
    if args:
        print args
    else:
        print 'why are we here'
    while True:
        if get_stream.downloader:
            status = yield get_stream.downloader.status()
            logger.debug('Status: %s', status.running_status)
            if status.running_status != 'running':
                break
            yield sleep(10)
    defer.returnValue(True)

    
def setup_sd_identifier(session, download_directory):
    sd_identifier = StreamDescriptor.StreamDescriptorIdentifier()
    LBRYFileOptions.add_lbry_file_to_sd_identifier(sd_identifier)

    stream_info_manager = LBRYFileMetadataManager.TempLBRYFileMetadataManager()
    file_saver_factory = LBRYFileDownloader.LBRYFileSaverFactory(
        session.peer_finder,
        session.rate_limiter,
        session.blob_manager,
        stream_info_manager,
        session.wallet,
        download_directory
    )
    sd_identifier.add_stream_downloader_factory(
        LBRYStreamDescriptor.LBRYFileStreamType, file_saver_factory)
    return sd_identifier


def download_stream(get_stream, name, stream_info):
    return get_stream.start(stream_info, name)


def log_and_stop(err):
    log.err(err)
    reactor.stop()


def print_(*args):
    sys.stdout.write(' '.join([str(a) for a in args]) + '\n')


def configureConsoleLogger(logger=None):
    logger = logger or logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(DEFAULT_FORMATTER)
    logger.addHandler(handler)
    logger.setLevel(level=logging.DEBUG)


def eatarg(fn, *args, **kwargs):
    """
    Returns a callback that takes one argument which is ignored and instead the
    underlying function is called.
    """
    return lambda _: fn(*args, **kwargs)


@defer.inlineCallbacks
def print_balance(wallet):
    balance = yield wallet.get_balance()
    print 'Balance:', balance


@defer.inlineCallbacks
def print_stream_info(wallet, name):
    stream_info = yield wallet.get_stream_info_for_name(name)
    print 'stream info:'
    print stream_info
    defer.returnValue(stream_info)


@defer.inlineCallbacks
def download_stream_identifier(session, stream_info):
    blob = yield StreamDescriptor.download_sd_blob(
        session,
        stream_info['sources']['lbry_sd_hash'],
        session.base_payment_rate_manager
    )
    logger.info('Downloaded blob: %s', blob)
    defer.returnValue(blob)


if __name__ == '__main__':
    sys.exit(main())
