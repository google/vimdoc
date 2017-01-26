import unittest

import vimdoc
from vimdoc.block import Block
from vimdoc import error
from vimdoc import module

class TestVimModule(unittest.TestCase):

  def test_section(self):
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    intro = Block(vimdoc.SECTION)
    intro.Local(name='Introduction', id='intro')
    main_module.Merge(intro)
    main_module.Close()
    self.assertEqual([intro], list(main_module.Chunks()))

  def test_duplicate_section(self):
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    intro = Block(vimdoc.SECTION)
    intro.Local(name='Introduction', id='intro')
    main_module.Merge(intro)
    intro2 = Block(vimdoc.SECTION)
    intro2.Local(name='Intro', id='intro')
    with self.assertRaises(error.DuplicateSection) as cm:
      main_module.Merge(intro2)
    self.assertEqual(('Duplicate section intro defined.',), cm.exception.args)

  def test_default_section_ordering(self):
    """Sections should be ordered according to documented built-in ordering."""
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    intro = Block(vimdoc.SECTION)
    intro.Local(name='Introduction', id='intro')
    commands = Block(vimdoc.SECTION)
    commands.Local(name='Commands', id='commands')
    about = Block(vimdoc.SECTION)
    about.Local(name='About', id='about')
    # Merge in arbitrary order.
    main_module.Merge(commands)
    main_module.Merge(about)
    main_module.Merge(intro)
    main_module.Close()
    self.assertEqual([intro, commands, about], list(main_module.Chunks()))

  def test_manual_section_ordering(self):
    """Sections should be ordered according to explicitly configured order."""
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    intro = Block(vimdoc.SECTION)
    intro.Local(name='Introduction', id='intro')
    # Configure explicit order.
    intro.Global(order=['commands', 'about', 'intro'])
    commands = Block(vimdoc.SECTION)
    commands.Local(name='Commands', id='commands')
    about = Block(vimdoc.SECTION)
    about.Local(name='About', id='about')
    # Merge in arbitrary order.
    main_module.Merge(commands)
    main_module.Merge(about)
    main_module.Merge(intro)
    main_module.Close()
    self.assertEqual([commands, about, intro], list(main_module.Chunks()))

  def test_child_sections(self):
    """Sections should be ordered after their parents."""
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    first = Block(vimdoc.SECTION)
    first.Local(name='Section 1', id='first')
    # Configure explicit order.
    first.Global(order=['first', 'second', 'third'])
    second = Block(vimdoc.SECTION)
    second.Local(name='Section 2', id='second')
    third = Block(vimdoc.SECTION)
    third.Local(name='Section 3', id='third')
    child11 = Block(vimdoc.SECTION)
    child11.Local(name='child11', id='child11', parent_id='first')
    child12 = Block(vimdoc.SECTION)
    child12.Local(name='child12', id='child12', parent_id='first')
    child21 = Block(vimdoc.SECTION)
    child21.Local(name='child21', id='child21', parent_id='second')
    # Merge in arbitrary order.
    for m in [second, child12, third, child11, first, child21]:
      main_module.Merge(m)
    main_module.Close()
    self.assertEqual(
        [first, child11, child12, second, child21, third],
        list(main_module.Chunks()))

  def test_missing_parent(self):
    """Parent sections should exist."""
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    first = Block(vimdoc.SECTION)
    first.Local(name='Section 1', id='first')
    second = Block(vimdoc.SECTION)
    second.Local(name='Section 2', id='second', parent_id='missing')
    main_module.Merge(first)
    main_module.Merge(second)
    with self.assertRaises(error.NoSuchParentSection) as cm:
      main_module.Close()
    expected = (
        'Section Section 2 has non-existent parent missing. '
        'Try setting the id of the parent section explicitly.')
    self.assertEqual((expected,), cm.exception.args)

  def test_ordered_child(self):
    """Child sections should not be included in @order."""
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    first = Block(vimdoc.SECTION)
    first.Local(name='Section 1', id='first')
    second = Block(vimdoc.SECTION)
    second.Local(name='Section 2', id='second', parent_id='first')
    first.Global(order=['first', 'second'])
    main_module.Merge(first)
    main_module.Merge(second)
    with self.assertRaises(error.OrderedChildSections) as cm:
      main_module.Close()
    self.assertEqual(("Child section second included in ordering ['first', 'second'].",), cm.exception.args)

  def test_partial_ordering(self):
    """Always respect explicit order and prefer built-in ordering.

    Undeclared built-in sections will be inserted into explicit order according
    to default built-in ordering. The about section should come after custom
    sections unless explicitly ordered."""
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    intro = Block(vimdoc.SECTION)
    intro.Local(name='Introduction', id='intro')
    # Configure explicit order.
    intro.Global(order=['custom1', 'intro', 'custom2'])
    commands = Block(vimdoc.SECTION)
    commands.Local(name='Commands', id='commands')
    about = Block(vimdoc.SECTION)
    about.Local(name='About', id='about')
    custom1 = Block(vimdoc.SECTION)
    custom1.Local(name='Custom1', id='custom1')
    custom2 = Block(vimdoc.SECTION)
    custom2.Local(name='Custom2', id='custom2')
    # Merge in arbitrary order.
    for section in [commands, custom2, about, intro, custom1]:
      main_module.Merge(section)
    main_module.Close()
    self.assertEqual([custom1, intro, commands, custom2, about],
        list(main_module.Chunks()))
