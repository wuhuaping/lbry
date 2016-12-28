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


log = logging.getLogger('main')


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=conf.server_port, nargs='+')
    parser.add_argument('--names', nargs='*')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args(args)

    log_support.configure_console(level='INFO')

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
    assert session.wallet
    run(session, args.destination, args.names, args.limit)
    reactor.run()


def safe_makedirs(directory):
    try:
        os.makedirs(directory)
    except OSError:
        pass


@defer.inlineCallbacks
def run(session, destinations, names, limit):
    try:
        yield session.setup()
        while not session.wallet.network.is_connected():
            log.info('Retrying wallet startup')
            try:
                yield session.wallet.start()
            except ValueError:
                pass
        names = yield getNames(session.wallet, names)
        if limit and limit < len(names):
            names = random.sample(names, limit)
        log.info('Processing %s names', len(names))
        t = Tracker(session, destinations, names)
        yield t.processNameClaims()
    except Exception:
        log.exception('Something bad happened')
    finally:
        log.warning('We are stopping the reactor gracefully')
        reactor.stop()


@defer.inlineCallbacks
def getNames(wallet, names):
    if names:
        defer.returnValue(names)
    nametrie = yield wallet.get_nametrie()
    defer.returnValue(list(getNameClaims(nametrie)))


def logAndStop(err):
    log_support.failure(err, log, 'This sucks: %s')
    reactor.stop()


def logAndRaise(err):
    log_support.failure(err, log, 'This still sucks: %s')
    return err



class Tracker(object):
    def __init__(self, session, destinations, names):
        self.session = session
        self.destinations = destinations
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
        try:
            log.info('Starting to get name claims')
            yield self._getSdHashes()
            self._filterNames('sd_hash')
            log.info('Downloading all of the blobs')
            yield self._downloadAllBlobs()
            log.info('Sending the blobs')
            yield self._sendSdBlobs()
        except Exception:
            log.exception('Something bad happened')

    def _getSdHashes(self):
        return DeferredPool((n.setSdHash(self.wallet) for n in self.names), 10)

    def _filterNames(self, attr):
        self.names = [n for n in self.names if getattr(n, attr)]
        self.stats[attr] = len(self.names)
        print("We have {} names with attribute {}".format(len(self.names), attr))

    def attempts_counter(self):
        return collections.Counter([n.availability_attempts for n in self.names])

    def _downloadAllBlobs(self):
        return DeferredPool((n.download_sd_blob(self.session) for n in self.names), 10)

    @defer.inlineCallbacks
    def _sendSdBlobs(self):
        blobs = [n.sd_blob for n in self.names if n.sd_blob]
        log.info('Sending %s blobs', len(blobs))
        blob_hashes = [b.blob_hash for b in blobs]
        for destination in self.destinations:
            factory = reflector.BlobClientFactory(self.blob_manager, blob_hashes, logBlobSent)
            yield self._connect(destination, factory)

    @defer.inlineCallbacks
    def _connect(self, destination, factory):
        url, port = destination
        ip = yield reactor.resolve(url)
        try:
            print('Connecting to {}'.format(ip))
            yield reactor.connectTCP(ip, port, factory)
            #factory.finished_deferred.addTimeout(60, reactor)
            value = yield factory.finished_deferred
            if value:
                print('Success!')
            else:
                print('Not success?', value)
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
        except Exception:
            log.exception('What happened')

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
    d.addTimeout(random.randint(10, 30), reactor)
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


class DeferredPool(defer.Deferred):
    def __init__(self, deferred_iter, pool_size):
        self.deferred_iter = deferred_iter
        self.pool_size = pool_size
        # results are returned unordered
        self.result_list = []
        self.started_count = 0
        self.total_count = None
        defer.Deferred.__init__(self)

        for deferred in itertools.islice(deferred_iter, pool_size):
            self._start_one(deferred)

    def _start_one(self, deferred):
        deferred.addCallbacks(self._callback, self._callback,
                              callbackArgs=(self.started_count, defer.SUCCESS),
                              errbackArgs=(self.started_count, defer.FAILURE))
        # TODO: remove this line when things are working
        deferred.addErrback(log.fail(), 'What happened')
        self.started_count += 1

    def _callback(self, result, index, success):
        print('Got result for', index)
        self.result_list.append((index, success, result))
        if self._done():
            self._finish()
        else:
            self._process_next()
        return result

    def _done(self):
        return self.total_count  == len(self.result_list)

    def _finish(self):
        result_list = [(s, r) for i, s, r in sorted(self.result_list)]
        self.callback(result_list)

    def _process_next(self):
        try:
            deferred = next(self.deferred_iter)
        except StopIteration:
            self.total_count = self.started_count
        else:
            self._start_one(deferred)


if __name__ == '__main__':
    sys.exit(main())
