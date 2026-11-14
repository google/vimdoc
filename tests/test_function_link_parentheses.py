import unittest

from vimdoc import module
from vimdoc import output


class TestFunctionLinkParentheses(unittest.TestCase):

  def setUp(self):
    self.writer = output.Helpfile(
        module.Module('example', module.VimPlugin('example')), '.')

  def test_function_call_spelling_matches_plain_name(self):
    self.assertEqual('See |foo#Bar()| and |foo#Bar()|.', self.writer.Expand(
        'See @function(foo#Bar()) and @function(foo#Bar).', None))

  def test_relative_function_name_with_parentheses(self):
    self.assertEqual('|example#Bar()|', self.writer.Expand(
        '@function(#Bar())', 'example#'))

  def test_unknown_directive_keeps_its_parentheses(self):
    self.assertEqual('@unknown(Foo())', self.writer.Expand('@unknown(Foo())', None))
