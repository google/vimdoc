import argparse
import os

import vimdoc

try:
    import shtab
except ImportError:
    from . import _shtab as shtab


def Source(path):
  if not os.path.isdir(path):
    raise argparse.ArgumentTypeError('{} not found'.format(path))
  if not os.access(path, os.R_OK):
    raise argparse.ArgumentTypeError('Cannot access {}'.format(path))
  return path


parser = argparse.ArgumentParser('vimdoc', description='Generate vim helpfiles')
shtab.add_argument_to(parser)
parser.add_argument('plugin', type=Source, metavar='PLUGIN').complete = shtab.DIR
parser.add_argument('--version', action='version',
    version='%(prog)s ' + vimdoc.__version__)
