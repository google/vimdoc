import unittest

from vimdoc import parser


class TestUsageMetadata(unittest.TestCase):

  def parse(self, directives):
    source = ['""'] + ['" ' + line for line in directives]
    source.append('function! x#Foo(X, ...)')
    return list(parser.ParseBlocks(source, 'autoload/x.vim'))

  def test_dictionary_before_first_usage_applies_to_all_usages(self):
    blocks = self.parse([
        '@dict SomeDict',
        '@usage {X}',
        'First usage.',
        '@usage {X} [Y]',
        'Second usage.',
        '@usage {X} [Y] [Z]',
    ])
    self.assertEqual(['SomeDict.Foo'] * 3,
                     [block.FullName() for block in blocks])

  def test_public_before_first_usage_applies_to_all_usages(self):
    blocks = self.parse(['@public', '@usage {X}', '@usage {X} [Y]'])
    self.assertEqual([False, False],
                     [block.locals.get('private') for block in blocks])

  def test_directives_after_a_usage_remain_local_to_that_usage(self):
    blocks = self.parse([
        '@usage {X}', '@dict SomeDict', '@usage {X} [Y]'])
    self.assertEqual(['SomeDict.Foo', 'x#Foo'],
                     [block.FullName() for block in blocks])
