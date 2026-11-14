import io
import unittest

from vimdoc import module
from vimdoc import output
from vimdoc import parser


class TestConsecutiveExamples(unittest.TestCase):

  def render(self, body):
    source = ['""', '" @section Examples'] + ['" ' + line for line in body]
    block, = parser.ParseBlocks(source, 'plugin/example.vim')
    block.Local(namespace=None)
    writer = output.Helpfile(module.Module('example', module.VimPlugin('example')), '.')
    writer.file = io.StringIO()
    writer.WriteParagraphs(block)
    return writer.file.getvalue()

  def test_adjacent_examples_use_one_boundary_line(self):
    actual = self.render(['Example: >', '  call Foo()', '< >', '  call Bar()', '<'])
    self.assertEqual('Example:\n>\n  call Foo()\n< >\n  call Bar()\n<\n\n', actual)

  def test_three_adjacent_examples_have_two_boundaries(self):
    actual = self.render(['>', '  call One()', '< >', '  call Two()',
                          '< >', '  call Three()', '<'])
    self.assertEqual(2, actual.count('< >\n'))

  def test_explicitly_separated_examples_remain_separate(self):
    actual = self.render(['>', '  call Foo()', '<', '', '>', '  call Bar()', '<'])
    self.assertNotIn('< >', actual)
    self.assertIn('<\n\n', actual)
