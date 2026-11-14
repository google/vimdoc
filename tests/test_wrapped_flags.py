import unittest

from vimdoc import paragraph
from vimdoc import parser


class TestWrappedFlags(unittest.TestCase):

  def test_flag_name_on_continuation_line(self):
    source = ['""', '" Example flag.', 'call s:plugin.Flag(',
              r"    \ 'example', 'value')"]
    block, = parser.ParseBlocks(source, 'plugin/example.vim')
    self.assertEqual('example', block.FullName())
    self.assertEqual(["Default: 'value' `"],
                     [p.text for p in block.paragraphs
                      if isinstance(p, paragraph.ListItem)])

  def test_whitespace_after_open_parenthesis(self):
    for whitespace in [' ', '\t', '    ']:
      with self.subTest(whitespace=whitespace):
        line = 'call s:plugin.Flag(' + whitespace + '"example", 3)'
        block, = parser.ParseBlocks(['""', '" Example flag.', line], 'example.vim')
        self.assertEqual('example', block.FullName())
