"""Vimdoc: Vim helpfile generation."""
import sys

try:
  from vimdoc._version import __version__ as __version__
except ImportError:
  import warnings
  warnings.warn('Failed to load __version__ from setuptools-scm')
  __version__ = '__unknown__'


# Don't even try to run under python 2 or earlier. It will seem to work but fail
# in corner cases with strange encoding errors.
if sys.version_info[0] < 3:
  raise ImportError('Python < 3 is unsupported')


SECTION = 'SECTION'
BACKMATTER = 'BACKMATTER'
EXCEPTION = 'EXCEPTION'
DICTIONARY = 'DICTIONARY'
FUNCTION = 'FUNCTION'
COMMAND = 'COMMAND'
SETTING = 'SETTING'
FLAG = 'FLAG'
