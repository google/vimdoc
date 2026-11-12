import unittest

import vimdoc
from vimdoc import module
from vimdoc import parser


class TestOverloadLinks(unittest.TestCase):

  def plugin(self, definition):
    source = ['""', '" @usage {x}', '" First usage.',
              '" @usage {x} [y]', '" Second usage.',
              '" @all']
    if definition.startswith('function'):
      source.append('" @public')
    source.append(definition)
    plugin = module.VimPlugin('example')
    for block in parser.ParseBlocks(source, 'plugin/example.vim'):
      plugin.Merge(block)
    return plugin

  def test_link_to_overloaded_function_uses_primary_tag(self):
    plugin = self.plugin('function! foo#Bar(x, ...) abort')
    self.assertEqual('foo#Bar()', plugin.LookupTag(vimdoc.FUNCTION, 'foo#Bar'))

  def test_link_to_overloaded_command_uses_primary_tag(self):
    plugin = self.plugin('command! -nargs=+ Bar echo <q-args>')
    self.assertEqual(':Bar', plugin.LookupTag(vimdoc.COMMAND, 'Bar'))
    self.assertEqual(':Bar', plugin.LookupTag(vimdoc.COMMAND, ':Bar'))

  def test_duplicate_definitions_still_raise(self):
    plugin = self.plugin('function! foo#Bar(x, ...) abort')
    block, = parser.ParseBlocks(
        ['""', '" @public', 'function! foo#Bar(x, ...) abort'],
        'plugin/other.vim')
    plugin.Merge(block)
    with self.assertRaises(KeyError):
      plugin.LookupTag(vimdoc.FUNCTION, 'foo#Bar')
