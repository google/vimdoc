"""Distribution for vimdoc."""
from distutils.core import setup
import io
import os.path
import sys


# Don't even try to run under python 2 or earlier. It will seem to work but fail
# in corner cases with strange encoding errors.
if sys.version_info[0] < 3:
  sys.exit('ERROR: Python < 3 is unsupported.')


VERSION_PATH = os.path.join(os.path.dirname(__file__), 'vimdoc/VERSION.txt')
with io.open(VERSION_PATH, 'r', encoding='utf-8') as f:
  version = f.read().strip()

LONG_DESCRIPTION = """
Vimdoc is a system for automatically generating vim help files from doc
comments embedded in vim plugin files.
""".strip()

setup(
    name='vimdoc',
    version=version,
    description='Generate vim helpfiles',
    long_description=LONG_DESCRIPTION,
    author='Nate Soares',
    author_email='nate@so8r.es',
    license='Apache 2.0',
    url='https://github.com/google/vimdoc',
    packages=['vimdoc'],
    scripts=[
        'scripts/vimdoc',
    ],
    extras_require={'completion': ['shtab']},
    package_data={'vimdoc': ['VERSION.txt']},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Documentation',
    ],
)
