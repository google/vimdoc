import unittest

import vimdoc
from vimdoc.block import Block
from vimdoc import error
from vimdoc import module

class TestVimPlugin(unittest.TestCase):

  def test_section(self):
    plugin = module.VimPlugin('myplugin')
    main_module = module.Module('myplugin', plugin)
    intro = Block(vimdoc.SECTION)
    intro.Local(name='Introduction', id='intro')
    main_module.Merge(intro)
    self.assertEquals(list(main_module.Chunks()), [intro])

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
    self.assertEquals(cm.exception.args, ('Duplicate section intro defined.',))
