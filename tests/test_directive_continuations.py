import unittest

from vimdoc import paragraph
from vimdoc import parser


class TestDirectiveContinuations(unittest.TestCase):

  def test_throws_description_continues_with_four_spaces(self):
    source = ['""', '" @throws Ambiguous if {name} refers to multiple sources within one',
              '"     namespace.', 'function! example#Find(name)']
    block, = parser.ParseBlocks(source, 'autoload/example.vim')
    description, = [p.description for p in block.paragraphs
                    if isinstance(p, paragraph.ExceptionLine)]
    self.assertEqual('if {name} refers to multiple sources within one namespace.',
                     description)

  def test_order_continues_across_multiple_lines(self):
    parsed = list(parser.EnumerateParsedLines([
        '""', '" @order intro', '"     commands', '"     about']))
    self.assertEqual(['intro', 'commands', 'about'], parsed[0][1].order)
    self.assertEqual(1, parsed[0][0])

  def test_unindented_description_is_a_separate_paragraph(self):
    source = ['""', '" @throws Example first.', '" Separate paragraph.',
              'function! example#Find()']
    block, = parser.ParseBlocks(source, 'autoload/example.vim')
    self.assertEqual('first.', block.paragraphs[0].description)
    self.assertEqual('Separate paragraph.', block.paragraphs[1].text)

  def test_tagline_joins_as_one_value(self):
    parsed = list(parser.EnumerateParsedLines(
        ['""', '" @tagline First part', '"     second part']))
    self.assertEqual('First part second part', parsed[0][1].tagline)

  def test_usage_descriptions_are_not_joined_to_the_header(self):
    parsed = list(parser.EnumerateParsedLines(
        ['""', '" @usage {name}', '"     Indented description.']))
    self.assertEqual(2, len(parsed))
    self.assertEqual('    Indented description.', parsed[1][1].line)
