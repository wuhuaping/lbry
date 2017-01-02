import sys

import theseus

from lbrynet.lbrynet_daemon import DaemonControl


def main():
    tracer = theseus.Tracer()
    print tracer
    tracer.install()
    try:
        DaemonControl.start()
    finally:
        with open('callgrind.theseus', 'wb') as outfile:
            tracer.write_data(outfile)


if __name__ == '__main__':
    sys.exit(main())
