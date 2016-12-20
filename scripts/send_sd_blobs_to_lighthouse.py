from __future__ import print_function
from lbrynet.core import log_support

import argparse
import collections
import itertools
import logging
import os
import random
import sys

import appdirs
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import endpoints

from lbrynet import conf
from lbrynet.core import Error
from lbrynet.core import Wallet
from lbrynet.core import BlobAvailability
from lbrynet.core import BlobManager
from lbrynet.core import HashAnnouncer
from lbrynet.core import PeerManager
from lbrynet.core import Session
from lbrynet.core import utils
from lbrynet.core.client import DHTPeerFinder
from lbrynet.dht import node
from lbrynet.metadata import Metadata
from lbrynet.core import StreamDescriptor as sd
from lbrynet import reflector


log = logging.getLogger()


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=conf.server_port)
    parser.add_argument('names', nargs='*')
    args = parser.parse_args(args)

    log_support.configure_console(level='DEBUG')

    db_dir = appdirs.user_data_dir('lighthouse-uploader')
    safe_makedirs(db_dir)
    # no need to persist metadata info
    storage = Wallet.InMemoryStorage()
    wallet = Wallet.LBRYumWallet(storage)
    blob_dir = os.path.join(db_dir, 'blobfiles')
    safe_makedirs(blob_dir)
    # Don't set a hash_announcer, we have no need to tell anyone we
    # have these blobs
    blob_manager = BlobManager.DiskBlobManager(None, blob_dir, db_dir)
    # TODO: make it so that I can disable the BlobAvailabilityTracker
    #       or, in general, make the session more reusable for users
    #       that only want part of the functionality
    session = Session.Session(
        blob_data_payment_rate=0,
        db_dir=db_dir,
        lbryid=utils.generate_id(),
        blob_dir=blob_dir,
        dht_node_port=4444,
        known_dht_nodes=conf.settings.known_dht_nodes,
        peer_port=3333,
        use_upnp=False,
        wallet=wallet,
        blob_manager=blob_manager,
    )
    run(session, args.destination, args.names)
    reactor.run()


def safe_makedirs(directory):
    try:
        os.makedirs(directory)
    except OSError:
        pass


@defer.inlineCallbacks
def run(session, destination, names):
    try:
        yield session.setup()
        names = yield getNames(session.wallet, names)
        t = Tracker(session, destination, names)
        yield t.processNameClaims()
    except Exception:
        log.exception('Something bad happened')
    finally:
        reactor.stop()


@defer.inlineCallbacks
def getNames(wallet, names):
    if names:
        defer.returnValue(names)
    nametrie = yield wallet.get_nametrie()
    defer.returnValue(getNameClaims(nametrie))


def logAndStop(err):
    log_support.failure(err, log, 'This sucks: %s')
    reactor.stop()


def logAndRaise(err):
    log_support.failure(err, log, 'This still sucks: %s')
    return err



class Tracker(object):
    def __init__(self, session, destination, names):
        self.session = session
        self.destination = destination
        self.names = [Name(n, self.blob_manager) for n in names]
        self.stats = {}

    @property
    def wallet(self):
        return self.session.wallet

    @property
    def blob_manager(self):
        return self.session.blob_manager

    @defer.inlineCallbacks
    def processNameClaims(self):
        log.info('Starting to get name claims')
        yield self._getSdHashes()
        self._filterNames('sd_hash')
        yield self._downloadAllBlobs()
        yield self._sendSdBlobs()

    def _getSdHashes(self):
        return defer.DeferredList([n.setSdHash(self.wallet) for n in self.names])

    def _filterNames(self, attr):
        self.names = [n for n in self.names if getattr(n, attr)]
        self.stats[attr] = len(self.names)
        print("We have {} names with attribute {}".format(len(self.names), attr))

    def attempts_counter(self):
        return collections.Counter([n.availability_attempts for n in self.names])

    def _downloadAllBlobs(self):
        return defer.DeferredList([n.download_sd_blob(self.session) for n in self.names])

    @defer.inlineCallbacks
    def _sendSdBlobs(self):
        blobs = [n.sd_blob for n in self.names if n.sd_blob]
        log.info('Sending %s blobs', len(blobs))
        blob_hashes = [b.blob_hash for b in blobs]
        factory = reflector.BlobClientFactory(self.blob_manager, blob_hashes, logBlobSent)
        ip = yield reactor.resolve(self.destination[0])
        try:
            print('Connecting to {}'.format(ip))
            yield reactor.connectTCP(ip, self.destination[1], factory)
            factory.finished_deferred.addTimeout(60, reactor)
            value = yield factory.finished_deferred
            if value:
                print('Success!')
        except Exception:
            log.exception('Somehow failed to send blobs')


def logBlobSent(sent, blob):
    if sent:
        print('Blob {} sent'.format(blob.blob_hash))
    else:
        print('Blob {} done'.format(blob.blob_hash))

class Name(object):
    def __init__(self, name, blob_manager):
        self.name = name
        self.blob_manager = blob_manager
        self.sd_hash = None
        self.sd_blob = None

    @defer.inlineCallbacks
    def setSdHash(self, wallet):
        try:
            stream = yield wallet.get_stream_info_for_name(self.name)
            metadata = Metadata.Metadata(stream)
            self.sd_hash = _getSdHash(metadata)
        except (Error.InvalidStreamInfoError, AssertionError):
            pass

    @defer.inlineCallbacks
    def download_sd_blob(self, session):
        print('Trying to get sd_blob for {} using {}'.format(self.name, self.sd_hash))
        try:
            blob = yield download_sd_blob_with_timeout(
                session, self.sd_hash, session.payment_rate_manager)
            self.sd_blob = blob
            yield self.blob_manager.blob_completed(blob)
            print('Downloaded sd_blob for {} using {}'.format(self.name, self.sd_hash))
        except defer.TimeoutError:
            print('Downloading sd_blob for {} timed-out'.format(self.name))
            # swallow errors from the timeout
            pass
        except Exception:
            log.exception('Failed to download {}'.format(self.name))

    def _setSdBlob(self, blob):
        print('{} has a blob'.format(self.name))



def download_sd_blob_with_timeout(session, sd_hash, payment_rate_manager, ):
    d = sd.download_sd_blob(session, sd_hash, payment_rate_manager)
    d.addTimeout(60, reactor)
    return d


def getNameClaims(trie):
    for x in trie:
        if 'txid' in x:
            try:
                yield str(x['name'])
            except UnicodeError:
                log.warning('Skippin name %s as it is not ascii', x['name'])


def _getSdHash(metadata):
    return metadata['sources']['lbry_sd_hash']


if __name__ == '__main__':
    sys.exit(main())
