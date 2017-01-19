from __future__ import print_function
from lbrynet.core import log_support

import argparse
import logging
import os
import random
import shutil
import sys
import tempfile

from twisted.internet import defer
from twisted.internet import reactor

from lbrynet import conf
from lbrynet.core import Wallet
from lbrynet.core import BlobAvailability
from lbrynet.core import Session
from lbrynet.core import utils
from lbrynet.core import StreamDescriptor

import common
import name
import pool
import track

log = logging.getLogger()


def main(args=None):
    conf.initialize_settings()
    log_support.configure_console()
    log_support.configure_twisted()

    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int)
    parser.add_argument('--name', type=str)
    args = parser.parse_args(args)

    # make a fresh dir or else we will include blobs that we've
    # already downloaded but might not otherwise be available.
    db_dir = tempfile.mkdtemp()
    try:
        blob_dir = os.path.join(db_dir, 'blobfiles')
        os.makedirs(blob_dir)
        storage = Wallet.InMemoryStorage()
        wallet = Wallet.LBRYumWallet(storage)
        session = Session.Session(
            0,
            db_dir=db_dir,
            lbryid=utils.generate_id(),
            blob_dir=blob_dir,
            dht_node_port=conf.settings['dht_node_port'],
            known_dht_nodes=conf.settings['known_dht_nodes'],
            peer_port=conf.settings['peer_port'],
            use_upnp=False,
            wallet=wallet
        )
        run(args, session)
        reactor.run()
    finally:
        shutil.rmtree(db_dir)


@defer.inlineCallbacks
def run(args, session):
    retry_connection = True
    while retry_connection:
        try:
            yield session.setup()
            retry_connection = False
            names = yield common.getNames(session.wallet)
            if args.name:
                names = [args.name]
            elif args.limit and len(names) > args.limit:
                names = random.sample(list(names), args.limit)
            names = [Name(n) for n in names]
            blob_tracker = BlobAvailability.BlobAvailabilityTracker(
                session.blob_manager, session.peer_finder, session.dht_node)

            tracker = yield AvailabilityGetter(session, names[0], blob_tracker)
            yield tracker.do_your_thang()
        except defer.FirstError:
            log.warning('Connection failed, retrying.')
        except Exception:
            log.exception('Something bad happened')
            retry_connection = False
    reactor.stop()


class AvailabilityGetter(object):
    def __init__(self, session, claim_name, blob_tracker):
        self.session = session
        self.name = claim_name
        self.blob_tracker = blob_tracker

    @defer.inlineCallbacks
    def do_your_thang(self):
        try:
            yield self.name.set_sd_hash(self.session.wallet)
            if self.name.sd_hash is None:
                log.error('NO SD HASH FOR {}'.format(self.name.name))
                return
            log.info('sd hash found')

            peer_counts = yield self.blob_tracker.get_blob_availability(self.name.sd_hash)
            assert len(peer_counts) == 1
            assert self.name.sd_hash in peer_counts
            peer_count = peer_counts[self.name.sd_hash]
            if peer_count == 0:
                log.error('NO PEERS FOR SD HASH FOR {}'.format(self.name.name))
                return
            log.info('sd hash has {} peers'.format(peer_count))

            try:
                sd_blob = yield StreamDescriptor.download_sd_blob(
                    self.session, self.name.sd_hash, self.session.payment_rate_manager)
                log.info('Downloaded sd_blob')
            except defer.TimeoutError:
                log.error('Downloading sd_blob for timed out')
                # swallow errors from the timeout
                pass
            except Exception:
                log.exception('Failed to download sd_blob')

            reader = StreamDescriptor.BlobStreamDescriptorReader(sd_blob)
            blob_data = yield reader.get_info()

            for blob_info in blob_data['blobs']:
                if 'blob_hash' in blob_info:
                    print(blob_info['blob_hash'])
                else:
                    print("NO BLOB HASH FOR BLOB")
                    print(blob_info)

        except Exception:
            log.exception('Something bad happened')








class Tracker(track.Tracker):
    def __init__(self, session, names, blob_tracker):
        track.Tracker.__init__(self, session, names)
        self.blob_tracker = blob_tracker

    @defer.inlineCallbacks
    def process_name_claims(self):
        try:
            log.warn('NAMES: ' + ', '.join([n.name for n in self.names]))
            yield self._get_sd_hashes()
            yield self._filter_names('sd_hash', quiet=True)
            log.warn('SD HASHES EXIST FOR: ' + ', '.join([n.name for n in self.names]))
            yield self._check_availability()
            yield self._filter_names('is_available', quiet=True)
            log.warn('AVAILABLE NAMES: ' + ', '.join([n.name for n in self.names]))
        except Exception:
            log.exception('Something bad happened')

    def _check_availability(self):
        return pool.DeferredPool(
            (n.check_availability(self.blob_tracker) for n in self.names),
            10
        )


class Name(name.Name):
    # From experience, very few sd_blobs get found after the third attempt
    MAX_ATTEMPTS = 3

    def __init__(self, my_name):
        name.Name.__init__(self, my_name)
        self.is_available = None
        self.availability_attempts = 0

    @defer.inlineCallbacks
    def _check_availability(self, blob_tracker):
        b = yield blob_tracker.get_blob_availability(self.sd_hash)
        peer_count = b[self.sd_hash]
        self.is_available = peer_count > 0
        if self.is_available:
            log.info('{} is available'.format(self.name))

    @defer.inlineCallbacks
    def check_availability(self, blob_tracker):
        while not self.is_available and self.availability_attempts < self.MAX_ATTEMPTS:
            self.availability_attempts += 1
            log.info('Attempt %s to find %s', self.availability_attempts, self.name)
            yield self._check_availability(blob_tracker)


if __name__ == '__main__':
    sys.exit(main())
