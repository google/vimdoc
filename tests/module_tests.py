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
