import os
import sys

import vimdoc.args
from vimdoc.module import Modules
from vimdoc.output import Helpfile


def main(argv=None):
  if argv is None:
    argv = sys.argv
  args = vimdoc.args.parser.parse_args(argv[1:])

  docdir = os.path.join(args.plugin, 'doc')
  if not os.path.isdir(docdir):
    os.mkdir(docdir)

  for module in Modules(args.plugin):
    Helpfile(module, docdir).Write()

if __name__ == '__main__':
  main()
