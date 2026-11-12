import unittest

from vimdoc import parser
from vimdoc import paragraph


class TestFlagDefaults(unittest.TestCase):

  def default(self, expression):
    source = ['""', '" A flag.',
              "call s:plugin.Flag('myflag', " + expression + ')']
    block, = parser.ParseBlocks(source, 'plugin/myplugin.vim')
    return [item.text for item in block.paragraphs
            if isinstance(item, paragraph.ListItem)]

  def test_nested_function_calls(self):
    expression = "get(split(s:foobar), 0, '')"
    self.assertEqual(['Default: ' + expression + ' `'], self.default(expression))

  def test_arbitrary_nesting_and_empty_calls(self):
    expression = 'outer(middle(inner(deep())))'
    self.assertEqual(['Default: ' + expression + ' `'], self.default(expression))

  def test_parentheses_inside_strings_are_not_delimiters(self):
    for expression in ["')'", "'(''quoted)('' text'", r'"a\")b("',
                       '[1, {"value": nested()}]']:
      with self.subTest(expression=expression):
        self.assertEqual(['Default: ' + expression + ' `'], self.default(expression))

  def test_line_continuations_preserve_nested_default(self):
    source = ['""', '" A flag.', "call s:plugin.Flag('myflag',",
              r"  \ get(split(s:foobar), 0, '')", r'  \ )']
    block, = parser.ParseBlocks(source, 'plugin/myplugin.vim')
    self.assertEqual("Default: get(split(s:foobar), 0, '') `",
                     block.paragraphs[-1].text)

  def test_incomplete_default_is_omitted(self):
    source = ['""', '" A flag.', "call s:plugin.Flag('myflag', nested("]
    block, = parser.ParseBlocks(source, 'plugin/myplugin.vim')
    self.assertEqual(['A flag.'], [item.text for item in block.paragraphs])
