import unittest
import warnings

from vimdoc import error
from vimdoc import parser


class TestCommandArgumentWarnings(unittest.TestCase):

  def parse(self, definition, documentation):
    source = ['""'] + ['" ' + line for line in documentation] + [definition]
    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter('always', error.ArgumentMismatch)
      list(parser.ParseBlocks(source, 'plugin/example.vim'))
    return [item for item in caught if issubclass(item.category, error.ArgumentMismatch)]

  def test_required_argument_for_zero_argument_command_warns(self):
    caught = self.parse('command! -nargs=0 Example echo 1', ['Takes {value}.'])
    self.assertEqual(1, len(caught))

  def test_optional_argument_for_implicit_zero_argument_command_warns(self):
    caught = self.parse('command! Example echo 1', ['@usage [value]'])
    self.assertEqual(1, len(caught))

  def test_argument_accepting_commands_do_not_warn(self):
    for nargs in ['1', '?', '*', '+']:
      with self.subTest(nargs=nargs):
        self.assertEqual([], self.parse('command! -nargs=' + nargs + ' Example echo 1',
                                        ['Takes {value}.']))

  def test_builtin_command_modifiers_are_not_arguments(self):
    self.assertEqual([], self.parse('command! -range -bang -count Example echo 1',
                                    ['Runs the command.']))
