"""Reseed a file.

Given a file and a matching sd_blob,
re-chunk and encrypt the file, adding
the new blobs to the manager.
"""
import argparse
import binascii
import logging
import json
import os
import sys

from twisted.internet import defer
from twisted.internet import reactor
from twisted.protocols import basic

from lbrynet import conf
from lbrynet.core import BlobManager
from lbrynet.core import HashAnnouncer
from lbrynet.core import log_support
from lbrynet.cryptstream import CryptStreamCreator


log = logging.getLogger('reseed_file')


def main():
    conf.initialize_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('sd_blob', help='a json file containing a key and the IVs')
    args = parser.parse_args()
    log_support.configure_console()

    run(args)
    reactor.run()


@defer.inlineCallbacks
def run(args):
    try:
        yield reseed_file(args.input_file, args.sd_blob)
    except Exception as e:
        log.exception('Failed to reseed')
    finally:
        reactor.stop()


@defer.inlineCallbacks
def reseed_file(input_file, sd_blob):
    sd_blob = SdBlob.new_instance(sd_blob)
    db_dir = '/home/jobevers/tmp' #conf.settings['data_dir']
    blobfile_dir = os.path.join(db_dir, "blobfiles")
    announcer = HashAnnouncer.DummyHashAnnouncer()
    blob_manager = BlobManager.DiskBlobManager(announcer, blobfile_dir, db_dir)
    yield blob_manager.setup()
    creator = CryptStreamCreator.CryptStreamCreator(
        blob_manager, None, sd_blob.key(), sd_blob.iv_generator())
    file_sender = basic.FileSender()
    with open(input_file) as f:
        yield file_sender.beginFileTransfer(f, creator)
        yield creator.stop()


class SdBlob(object):
    def __init__(self, contents):
        self.contents = contents

    def key(self):
        return self.contents['key']

    def iv_generator(self):
        for blob_info in self.contents['blobs']:
            print blob_info['iv']
            yield binascii.unhexlify(blob_info['iv'])

    @classmethod
    def new_instance(cls, filename):
        with open(filename) as f:
            return cls(json.load(f))


if __name__ == '__main__':
    sys.exit(main())
