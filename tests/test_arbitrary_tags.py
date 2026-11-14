import io
import unittest

from vimdoc import module
from vimdoc import output
from vimdoc import parser


class TestArbitraryTags(unittest.TestCase):

  def writer(self):
    writer = output.Helpfile(module.Module('example', module.VimPlugin('example')), '.')
    writer.file = io.StringIO()
    return writer

  def test_tags_are_rendered_at_their_documented_position(self):
    source = ['""', '" @section Introduction', '" Before the tags.',
              '" @tag plugin[]', '" @tag plugin[commands]', '" After the tags.']
    block, = parser.ParseBlocks(source, 'plugin/example.vim')
    block.Local(namespace=None)
    writer = self.writer()
    writer.WriteParagraphs(block)
    text = writer.file.getvalue()
    self.assertLess(text.index('Before the tags.'), text.index('*plugin[]*'))
    self.assertLess(text.index('*plugin[]*'), text.index('*plugin[commands]*'))
    self.assertLess(text.index('*plugin[commands]*'), text.index('After the tags.'))

  def test_inline_tag_is_not_prefixed_with_plugin_name(self):
    self.assertEqual('Before *plugin[]* after',
                     self.writer().Expand('Before @tag(plugin[]) after', None))

  def test_long_tag_is_not_wrapped_or_rejected(self):
    tag = 'long-tag-' * 15
    block, = parser.ParseBlocks(['""', '" @section Introduction', '" @tag ' + tag],
                                'plugin/example.vim')
    block.Local(namespace=None)
    writer = self.writer()
    writer.WriteParagraphs(block)
    self.assertIn('*' + tag + '*\n', writer.file.getvalue())
