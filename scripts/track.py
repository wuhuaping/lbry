import logging

from twisted.internet import defer

import pool

log = logging.getLogger(__name__)


class Tracker(object):
    def __init__(self, session, names):
        self.session = session
        self.names = names
        self.stats = {}

    @property
    def wallet(self):
        return self.session.wallet

    @defer.inlineCallbacks
    def process_name_claims(self):
        try:
            log.info('Starting to get name claims')
            yield self._get_sd_hashes()
            self._filter_names('sd_hash')
            log.info('Downloading all of the blobs')
            yield self._download_all_blobs()
        except Exception:
            log.exception('Something bad happened')

    def _get_sd_hashes(self):
        return pool.DeferredPool((n.set_sd_hash(self.wallet) for n in self.names), 10)

    def _filter_names(self, attr, quiet=False):
        self.names = [n for n in self.names if getattr(n, attr)]
        self.stats[attr] = len(self.names)
        if not quiet:
            print("We have {} names with attribute {}".format(len(self.names), attr))

    def _download_all_blobs(self):
        return pool.DeferredPool((n.download_sd_blob(self.session) for n in self.names), 10)
