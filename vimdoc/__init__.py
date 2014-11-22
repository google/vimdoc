"""Vimdoc: Vim helpfile generation."""
import sys


# Don't even try to run under python 2 or earlier. It will seem to work but fail
# in corner cases with strange encoding errors.
if sys.version_info[0] < 3:
  raise ImportError('Python < 3 is unsupported')


def __read_version_txt():
  import pkgutil
  return pkgutil.get_data('vimdoc', 'VERSION.txt').decode('utf-8').strip()

__version__ = __read_version_txt()

SECTION = 'SECTION'
BACKMATTER = 'BACKMATTER'
EXCEPTION = 'EXCEPTION'
DICTIONARY = 'DICTIONARY'
FUNCTION = 'FUNCTION'
COMMAND = 'COMMAND'
SETTING = 'SETTING'
FLAG = 'FLAG'
