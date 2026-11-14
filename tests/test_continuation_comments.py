import unittest

from vimdoc import parser


class TestContinuationComments(unittest.TestCase):

  def test_comment_does_not_interrupt_code_continuation(self):
    source = ['echo', r"  \ 'first string'", r'  "\ Some comment',
              r"  \ 'second string'"]
    self.assertEqual([(0, "echo 'first string' 'second string'")],
                     list(parser.EnumerateStripNewlinesAndJoinContinuations(source)))

  def test_comment_before_code_keeps_original_line_number(self):
    source = [r'"\ Ignored comment', 'echo', r'  "\ Another comment', r"  \ 'text'"]
    self.assertEqual([(1, "echo 'text'")],
                     list(parser.EnumerateStripNewlinesAndJoinContinuations(source)))

  def test_ordinary_comment_still_cannot_continue_as_code(self):
    from vimdoc import error
    with self.assertRaises(error.CannotContinue):
      list(parser.EnumerateStripNewlinesAndJoinContinuations(['" Comment', r'  \ code']))
