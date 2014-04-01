"""Vimdoc plugin management."""
from collections import OrderedDict
import itertools
import json
import os
import warnings

import vimdoc
from vimdoc import error
from vimdoc import parser
from vimdoc.block import Block

MAIN = 0
AUTOLOAD = 1
GENERIC = 2

# Plugin subdirectories that should be crawled by vimdoc.
DOC_SUBDIRS = [
    'plugin',
    'instant',
    'autoload',
    'syntax',
    'indent',
    'ftdetect',
    'ftplugin',
]


class Module(object):
  """Manages a set of source files that all output to the same help file."""

  def __init__(self, name, blocks, namespace=None):
    self.name = name
    self.sections = OrderedDict()
    self.backmatters = {}
    self.collections = {}
    self.order = None
    self.tagline = None
    self.author = None
    self.stylization = None
    self.library = None

    blocklist = list(blocks)
    # The initial file had no blocks. We're done initializing.
    if not blocklist:
      return

    # The initial block has no explicit type. It's the intro section.
    if blocklist[0].locals.get('type') is True:
      blocklist[0].SetType(vimdoc.SECTION)
      blocklist[0].Local(name='Introduction', id='intro')
    # The first block is allowed to contain metadata if it's a SECTION.
    if blocklist[0].locals.get('type') == vimdoc.SECTION:
      self.ConsumeMetadata(blocklist[0])

    # The final block has no explicit type. It's the about section.
    if blocklist[-1].locals.get('type') is True:
      blocklist[-1].SetType(vimdoc.SECTION)
      blocklist[-1].Local(name='About', id='about')
    # The final block is allowed to contain metadata if it's SECTION/BACKMATTER.
    if blocklist[-1].locals.get('type') in [vimdoc.SECTION, vimdoc.BACKMATTER]:
      self.ConsumeMetadata(blocklist[-1])
    for block in blocklist:
      self.Merge(block, namespace=namespace)

  def ConsumeMetadata(self, block):
    assert block.locals.get('type') == 'SECTION'
    for control in ['order', 'author', 'stylization', 'library', 'tagline']:
      if control in block.globals:
        if getattr(self, control) is not None:
          raise error.RedundantControl(control)
        setattr(self, control, block.globals[control])
    block.globals.clear()

  def Inherit(self, module):
    if self.author is None:
      self.author = module.author
    if self.library is None:
      self.library = module.library

  def Merge(self, block, namespace=None):
    """Merges a block with the module."""
    # They would have been cleared by ConsumeMetadata if the block were allowed
    # to have globals.
    if block.globals:
      raise error.InvalidGlobals(block.globals)

    typ = block.locals.get('type')
    # This block doesn't want to be spoken to.
    if not typ:
      return
    # If the type still hasn't been set, it never will be.
    if typ is True:
      raise error.AmbiguousBlock
    # The inclusion of function docs depends upon the module type.
    if typ == vimdoc.FUNCTION:
      # Exclude deprecated functions
      if block.locals.get('deprecated'):
        return
      # If this is a library module, exclude private functions.
      if self.library and block.locals.get('private'):
        return
      # If this is a non-library, exclude non-explicitly-public functions.
      if not self.library and block.locals.get('private', True):
        return
      if 'exception' in block.locals:
        typ = vimdoc.EXCEPTION
    # Sections and Backmatter are specially treated.
    if typ == vimdoc.SECTION:
      self.sections[block.locals.get('id')] = block
    elif typ == vimdoc.BACKMATTER:
      self.backmatters[block.locals.get('id')] = block
    else:
      self.collections.setdefault(typ, []).append(block)
    block.Local(namespace=namespace)

  def LookupTag(self, typ, name):
    """Returns the tag name for the given type and name."""
    if typ not in self.collections:
      raise KeyError('Unrecognized lookup type: %s(%s)' % (typ, name))
    collection = self.collections[typ]
    # Support both @command(Name) and @command(:Name).
    fullname = (
        typ == vimdoc.COMMAND and name.lstrip(':') or name)
    candidates = [x for x in collection if x.FullName() == fullname]
    if not candidates:
      raise KeyError('%s "%s" not found' % (typ, name))
    if len(candidates) > 1:
      raise KeyError('Found multiple %ss named %s' % (typ, name))
    return candidates[0].TagName()

  def Close(self):
    """Closes the module.

    All default sections that have not been overridden will be created.
    """
    if vimdoc.FUNCTION in self.collections and 'functions' not in self.sections:
      functions = Block()
      functions.SetType(vimdoc.SECTION)
      functions.Local(id='functions', name='Functions')
      self.Merge(functions)
    if (vimdoc.EXCEPTION in self.collections
        and 'exceptions' not in self.sections):
      exceptions = Block()
      exceptions.SetType(vimdoc.SECTION)
      exceptions.Local(id='exceptions', name='Exceptions')
      self.Merge(exceptions)
    if vimdoc.COMMAND in self.collections and 'commands' not in self.sections:
      commands = Block()
      commands.SetType(vimdoc.SECTION)
      commands.Local(id='commands', name='Commands')
      self.Merge(commands)
    if vimdoc.DICTIONARY in self.collections and 'dicts' not in self.sections:
      dicts = Block()
      dicts.SetType(vimdoc.SECTION)
      dicts.Local(id='dicts', name='Dictionaries')
      self.Merge(dicts)
    if ((vimdoc.FLAG in self.collections or
         vimdoc.SETTING in self.collections) and
        'config' not in self.sections):
      config = Block()
      config.SetType(vimdoc.SECTION)
      config.Local(id='config', name='Configuration')
      self.Merge(config)
    if not self.order:
      self.order = []
      for builtin in [
          'intro',
          'config',
          'commands',
          'autocmds',
          'settings',
          'dicts',
          'functions',
          'exceptions',
          'mappings',
          'about']:
        if builtin in self.sections or builtin in self.backmatters:
          self.order.append(builtin)
    for backmatter in self.backmatters:
      if backmatter not in self.sections:
        raise error.NoSuchSection(backmatter)
    known = set(itertools.chain(self.sections, self.backmatters))
    if known.difference(self.order):
      raise error.NeglectedSections(known)
    # Sections are now in order.
    for key in self.order:
      if key in self.sections:
        # Move to end.
        self.sections[key] = self.sections.pop(key)

  def Chunks(self):
    for ident, section in self.sections.items():
      yield section
      if ident == 'functions':
        # Sort by namespace, but preserve order within the same namespace. This
        # lets us avoid variability in the order files are traversed without
        # losing all useful order information.
        collection = sorted(
            self.collections.get(vimdoc.FUNCTION, ()),
            key=lambda x: x.locals.get('namespace', ''))
        for block in collection:
          if 'dict' not in block.locals and 'exception' not in block.locals:
            yield block
      if ident == 'commands':
        for block in self.collections.get(vimdoc.COMMAND, ()):
          yield block
      if ident == 'dicts':
        for block in sorted(self.collections.get(vimdoc.DICTIONARY, ())):
          yield block
          collection = sorted(
              self.collections.get(vimdoc.FUNCTION, ()),
              key=lambda x: x.locals.get('namespace', ''))
          for func in collection:
            if func.locals.get('dict') == block.locals['dict']:
              yield func
      if ident == 'exceptions':
        for block in self.collections.get(vimdoc.EXCEPTION, ()):
          yield block
      if ident == 'config':
        for block in self.collections.get(vimdoc.FLAG, ()):
          yield block
        for block in self.collections.get(vimdoc.SETTING, ()):
          yield block
      if ident in self.backmatters:
        yield self.backmatters[ident]


def Modules(directory):
  """Creates modules from a plugin directory.

  Note that there can be many, if a plugin has standalone parts that merit their
  own helpfiles.

  Args:
    directory: The plugin directory.
  Yields:
    Module objects as necessary.
  """
  directory = directory.rstrip(os.path.sep)
  addon_info = None
  # Check for module metadata in addon-info.json (if it exists).
  addon_info_path = os.path.join(directory, 'addon-info.json')
  if os.path.isfile(addon_info_path):
    try:
      with open(addon_info_path, 'r') as addon_info_file:
        addon_info = json.loads(addon_info_file.read())
    except (IOError, ValueError) as e:
      warnings.warn(
          'Failed to read file {}. Error was: {}'.format(addon_info_path, e),
          error.InvalidAddonInfo)
  plugin_name = None
  # Use plugin name from addon-info.json if available. Fall back to dir name.
  addon_info = addon_info or {}
  plugin_name = addon_info.get(
      'name', os.path.basename(os.path.abspath(directory)))
  docdir = os.path.join(directory, 'doc')
  if not os.path.isdir(docdir):
    os.mkdir(docdir)
  plugindir = os.path.join(directory, 'plugin')
  ftplugindir = os.path.join(directory, 'ftplugin')
  autoloaddir = os.path.join(directory, 'autoload')
  main_namespace = None
  old_standard_file = os.path.join(directory, 'plugin', plugin_name + '.vim')
  flags_file = os.path.join(directory, 'instant', 'flags.vim')
  if os.path.isfile(old_standard_file):
    mainfile = old_standard_file
  elif os.path.isfile(flags_file):
    mainfile = flags_file
  elif os.path.exists(os.path.join(directory, 'plugin')):
    mainfile = GuessMainFileIgnoringOthersPotentiallyContainingDirectives(
        plugindir)
  elif os.path.exists(os.path.join(directory, 'ftplugin')):
    mainfile = GuessMainFileIgnoringOthersPotentiallyContainingDirectives(
        ftplugindir)
  elif os.path.exists(os.path.join(directory, 'autoload')):
    main_autoload = os.path.join(directory, 'autoload', plugin_name + '.vim')
    if os.path.exists(main_autoload):
      mainfile = main_autoload
      filepath = os.path.relpath(main_autoload, autoloaddir)
      main_namespace = GetAutoloadNamespace(filepath)
    else:
      mainfile = None
  else:
    raise error.UnknownPluginType
  # The main file. The only one allowed to have sections.
  if mainfile:
    with open(mainfile) as filehandle:
      blocks = parser.ParseBlocks(filehandle, mainfile)
      module = Module(plugin_name, blocks, namespace=main_namespace)
  else:
    module = Module(plugin_name, [])
  standalones = []
  # Extension files. May have commands/settings/flags/functions.
  for (root, dirs, files) in os.walk(directory):
    # Prune non-standard top-level dirs like 'test'.
    if root == directory:
      dirs[:] = [x for x in dirs if x in DOC_SUBDIRS + ['after']]
    if root == os.path.join(directory, 'after'):
      dirs[:] = [x for x in dirs if x in DOC_SUBDIRS]
    for f in files:
      filename = os.path.join(root, f)
      if filename.endswith('.vim') and filename != mainfile:
        with open(filename) as filehandle:
          blocks = list(parser.ParseBlocks(filehandle, filename))
        if filename.startswith(autoloaddir):
          filepath = os.path.relpath(filename, autoloaddir)
          # We have to watch out. The file might be standalone. If it is,
          # the accompanying directory belongs to the standalone.
          # If autoload/foo.vim is standalone then so is autoload/foo/*.
          if blocks and blocks[0].globals.get('standalone'):
            standalone_name = os.path.splitext(filepath)[0].replace('/', '#')
            standalones.append((standalone_name, blocks))
            subdir = os.path.splitext(filename)[0]
            try:
              # Remove the accompanying directory.
              del dirs[dirs.index(subdir)]
            except ValueError:
              # There was no accompanying directory.
              pass
            continue
          namespace = GetAutoloadNamespace(filepath)
        else:
          namespace = None
        for block in blocks:
          module.Merge(block, namespace=namespace)
    # Set module metadata from addon-info.json.
    # Do this at the end to take precedence over vimdoc directives.
    if addon_info is not None:
      # Valid addon-info.json. Apply addon metadata.
      if 'author' in addon_info:
        module.author = addon_info['author']
      if 'description' in addon_info:
        module.tagline = addon_info['description']

  module.Close()
  yield module
  # Handle the standalone autoloadable files.
  for (name, blocks) in standalones:
    namespace = name + '#'
    submodule = Module(name, blocks, namespace=namespace)
    submodule.Inherit(module)
    for (root, dirs, files) in os.walk(os.path.join(autoloaddir, name)):
      namespace = root.replace('/', '#') + '#'
      for f in files:
        filename = os.path.join(root, f)
        if filename.endswith('.vim'):
          with open(filename) as filehandle:
            for block in parser.ParseBlocks(filehandle, filename):
              submodule.Merge(block, namespace=namespace)
    submodule.Close()
    yield submodule


def GetAutoloadNamespace(filepath):
  return (os.path.splitext(filepath)[0]).replace('/', '#') + '#'


def GuessMainFileIgnoringOthersPotentiallyContainingDirectives(directory):
  """Pick a file to check for plugin-level directives.

  This is a short-term hack. Eventually, vimdoc will process plugins more
  holistically and detect plugin directives in other files.

  Args:
    directory: The plugin directory.
  Returns:
    Path to "main" file, or None if no single "main" file is identified.
  """
  files = [f for f in os.listdir(directory)
           if os.path.isfile(os.path.join(directory, f))
           and f.endswith('.vim')]
  if len(files) == 1:
    return os.path.join(directory, files[0])
  return None
