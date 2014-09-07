"""Vimdoc: Vim helpfile generation."""

def __read_version_txt():
  import pkgutil
  return pkgutil.get_data('vimdoc', 'VERSION.txt').strip()

__version__ = __read_version_txt()

SECTION = 'SECTION'
BACKMATTER = 'BACKMATTER'
EXCEPTION = 'EXCEPTION'
DICTIONARY = 'DICTIONARY'
FUNCTION = 'FUNCTION'
COMMAND = 'COMMAND'
SETTING = 'SETTING'
FLAG = 'FLAG'
