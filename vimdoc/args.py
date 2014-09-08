import argparse
import os

import vimdoc


def Source(path):
  if not os.path.isdir(path):
    raise argparse.ArgumentTypeError('{} not found'.format(path))
  if not os.access(path, os.R_OK):
    raise argparse.ArgumentTypeError('Cannot access {}'.format(path))
  return path

parser = argparse.ArgumentParser(description='Generate vim helpfiles')
parser.add_argument('plugin', type=Source, metavar='PLUGIN')
parser.add_argument('--version', action='version',
    version='%(prog)s ' + vimdoc.__version__)
