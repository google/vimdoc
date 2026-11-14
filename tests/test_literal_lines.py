import io
import unittest

from vimdoc import module
from vimdoc import output
from vimdoc import parser


class TestLiteralLines(unittest.TestCase):

  def writer(self):
    writer = output.Helpfile(module.Module('example', module.VimPlugin('example')), '.')
    writer.file = io.StringIO()
    return writer

  def test_long_code_line_is_not_wrapped(self):
    text = '    call Example(' + 'long_argument, ' * 12 + 'last_argument)'
    writer = self.writer()
    writer.WriteCodeLine(text, None, indent=1)
    self.assertEqual('  ' + text + '\n', writer.file.getvalue())

  def test_literal_block_preserves_indentation_and_blank_lines(self):
    source = ['""', '" @section Examples', '" >',
              '"   if Condition()', '"     ' + 'echo "long" ' * 20,
              '"', '"   endif', '" <']
    block, = parser.ParseBlocks(source, 'plugin/example.vim')
    block.Local(namespace=None)
    writer = self.writer()
    writer.WriteParagraphs(block)
    expected = '\n>\n  if Condition()\n    ' + 'echo "long" ' * 20 + '\n\n  endif\n<\n\n'
    self.assertEqual(expected, writer.file.getvalue())
