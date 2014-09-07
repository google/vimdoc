"""Distribution for vimdoc."""
from distutils.core import setup
import os.path

with open(os.path.join(os.path.dirname(__file__), 'vimdoc/VERSION.txt')) as f:
  version = f.read().strip()

setup(
    name='vimdoc',
    version=version,
    description='Generate vim helpfiles',
    author='Nate Soares',
    author_email='nate@so8r.es',
    url='https://github.com/google/vimdoc',
    packages=[
        'vimdoc',
    ],
    scripts=[
        'scripts/vimdoc',
    ],
    package_data={'vimdoc': ['VERSION.txt']},
)
