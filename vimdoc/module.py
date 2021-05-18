"""Vimdoc plugin management."""
from collections import OrderedDict
import io
import json
import os
import warnings

import vimdoc
from vimdoc import error
from vimdoc import parser
from vimdoc import regex
from vimdoc.block import Block

# Plugin subdirectories that should be crawled by vimdoc.
DOC_SUBDIRS = [
    'plugin',
    'instant',
    'autoload',
    'syntax',
    'indent',
    'ftdetect',
    'ftplugin',
    'spell',
    'colors',
]


class Module(object):
  """Manages a set of source files that all output to the same help file."""

  def __init__(self, name, plugin):
    self.name = name
    self.plugin = plugin
    self.sections = OrderedDict()
    self.backmatters = {}
    self.collections = {}
    self.order = None

  def Merge(self, block, namespace=None):
    """Merges a block with the module."""
    typ = block.locals.get('type')

    # This block doesn't want to be spoken to.
    if not typ:
      return
    # If the type still hasn't been set, it never will be.
    if typ is True:
      raise error.AmbiguousBlock

    block.Local(namespace=namespace)
    # Consume module-level metadata
    if 'order' in block.globals:
      if self.order is not None:
        raise error.RedundantControl('order')
      self.order = block.globals['order']
    self.plugin.Merge(block)

    # Sections and Backmatter are specially treated.
    block_id = block.locals.get('id')
    if typ == vimdoc.SECTION:
      # Overwrite existing section if it's a default.
      if block_id not in self.sections or self.sections[block_id].IsDefault():
        self.sections[block_id] = block
      elif not block.IsDefault():
        # Tried to overwrite explicit section with explicit section.
        raise error.DuplicateSection(block_id)
    elif typ == vimdoc.BACKMATTER:
      # Overwrite existing section backmatter if it's a default.
      if (block_id not in self.backmatters
          or self.backmatters[block_id].IsDefault()):
        self.backmatters[block_id] = block
      elif not block.IsDefault():
        # Tried to overwrite explicit backmatter with explicit backmatter.
        raise error.DuplicateBackmatter(block_id)
    else:
      collection_type = self.plugin.GetCollectionType(block)
      if collection_type is not None:
        self.collections.setdefault(collection_type, []).append(block)

  def LookupTag(self, typ, name):
    return self.plugin.LookupTag(typ, name)

  def GetCollection(self, typ):
    """Gets a collection by type, sorting and filtering as necessary.

    Applies appropriate sorting for the type. Most types are left in the same
    order they were defined in the code since that's usually the logical order.
    Functions are sorted by namespace but functions within a namespace are left
    in definition order. Dicts are sorted by name.

    Some blocks might be "default blocks", meaning they should be omitted if any
    other block defines the same tag name. These will be omitted as appropriate.

    Args:
      typ: a vimdoc block type identifier (e.g., vimdoc.FUNCTION)
    """
    collection = self.collections.get(typ, ())
    if typ == vimdoc.FUNCTION:
      # Sort by namespace, but preserve order within the same namespace. This
      # lets us avoid variability in the order files are traversed without
      # losing all useful order information.
      collection = sorted(collection,
          key=lambda x: x.locals.get('namespace', ''))
    elif typ == vimdoc.DICTIONARY:
      collection = sorted(collection)
    non_default_names = set(x.TagName() for x in collection
        if not x.IsDefault())
    return [x for x in collection
        if not x.IsDefault() or x.TagName() not in non_default_names]

  def _AddMaktabaFlagHelp(self):
    """If any maktaba flags were documented, add a default configuration section
     to explain how to use them.
    """
    if self.GetCollection(vimdoc.FLAG):
      block = Block(vimdoc.SECTION, is_default=True)
      block.Local(id='config', name='Configuration')
      block.AddLine(
          'This plugin uses maktaba flags for configuration. Install Glaive'
          ' (https://github.com/google/glaive) and use the @command(Glaive)'
          ' command to configure them.')
      self.Merge(block)

  def Close(self):
    """Closes the module.

    All default sections that have not been overridden will be created.
    """
    # ----------------------------------------------------------
    # Add default sections.

    # type : (id, name)
    default_sections = [
        (vimdoc.FUNCTION, 'functions', 'Functions'),
        (vimdoc.EXCEPTION, 'exceptions', 'Exceptions'),
        (vimdoc.COMMAND, 'commands', 'Commands'),
        (vimdoc.DICTIONARY, 'dicts', 'Dictionaries'),
        (vimdoc.FLAG, 'config', 'Configuration'),
        (vimdoc.SETTING, 'config', 'Configuration'),
      ]

    for (typ, id, name) in default_sections:
      if typ == vimdoc.FLAG:
        self._AddMaktabaFlagHelp()

      if self.GetCollection(typ) and (id not in self.sections):
        # Create the section if it does not exist.
        block = Block(vimdoc.SECTION)
        block.Local(id=id, name=name)
        self.Merge(block)


    # ----------------------------------------------------------
    # Add backmatter.

    for backmatter in self.backmatters:
      if backmatter not in self.sections:
        raise error.NoSuchSection(backmatter)

    # ----------------------------------------------------------
    # Expand child sections and order the section list for output.

    # Use explicit order as partial ordering and merge with default section
    # ordering. All custom sections must be ordered explicitly.
    self.order = self._GetSectionOrder(self.order, self.sections)

    # Child section collection
    to_delete = []
    for key in self.sections:
      section = self.sections[key]
      parent_id = section.locals.get('parent_id', None)
      if parent_id:
        if parent_id not in self.sections:
          raise error.NoSuchParentSection(
                  section.locals['name'], parent_id)
        parent = self.sections[parent_id]
        parent.locals.setdefault('children', []).append(section)
        to_delete.append(key)

    for key in to_delete:
      self.sections.pop(key)

    # Check that all top-level sections are included in ordering.
    known = set(self.sections)
    neglected = sorted(known.difference(self.order))
    if neglected:
      raise error.NeglectedSections(neglected, self.order)

    # Reinsert top-level sections in the correct order, expanding the tree of
    # child sections along the way so we have a linear list of sections to pass
    # to the output functions.

    # Helper function to recursively add children to self.sections.
    # We add a 'level' variable to locals so that WriteTableOfContents can keep
    # track of the nesting.
    def _AddChildSections(section):
      section.locals.setdefault('level', 0)
      if 'children' in section.locals:
        sort_key = lambda s: s.locals['name']
        for child in sorted(section.locals['children'], key=sort_key):
          child.locals['level'] = section.locals['level'] + 1
          self.sections[child.locals['id']] = child
          _AddChildSections(child)

    # Insert sections according to the @order directive
    for key in self.order:
      if key in self.sections:
        section = self.sections.pop(key)
        if 'parent_id' in section.locals and section.locals['parent_id']:
          raise error.OrderedChildSections(section.locals['id'], self.order)
        # Move to end.
        self.sections[key] = section
        _AddChildSections(section)

  def Chunks(self):
    for ident, section in self.sections.items():
      yield section
      if ident == 'functions':
        for block in self.GetCollection(vimdoc.FUNCTION):
          if 'dict' not in block.locals and 'exception' not in block.locals:
            yield block
      if ident == 'commands':
        for block in self.GetCollection(vimdoc.COMMAND):
          yield block
      if ident == 'dicts':
        for block in self.GetCollection(vimdoc.DICTIONARY):
          yield block
          for func in self.GetCollection(vimdoc.FUNCTION):
            if func.locals.get('dict') == block.locals['dict']:
              yield func
      if ident == 'exceptions':
        for block in self.GetCollection(vimdoc.EXCEPTION):
          yield block
      if ident == 'config':
        for block in self.GetCollection(vimdoc.FLAG):
          yield block
        for block in self.GetCollection(vimdoc.SETTING):
          yield block
      if ident in self.backmatters:
        yield self.backmatters[ident]

  @staticmethod
  def _GetSectionOrder(explicit_order, sections):
    """Gets final section order from explicit_order and actual sections present.

    Built-in sections with no explicit order come before custom sections, with
    two exceptions:
      * The "about" section comes last by default.
      * If a built-in section is explicitly ordered, it "resets" the ordering so
        so that subsequent built-in sections come directly after it.
    This yields the order you would intuitively expect in cases like ordering
    "intro" after other sections.
    """
    order = explicit_order or []
    default_order = [
      'intro',
      'config',
      'commands',
      'autocmds',
      'settings',
      'dicts',
      'functions',
      'exceptions',
      'mappings']
    # Add any undeclared sections before custom sections, except 'about' which
    # comes at the end by default.
    section_insertion_idx = 0
    order = order[:]
    for builtin in default_order:
      if builtin in order:
        # Section already present. Skip and continue later sections after it.
        section_insertion_idx = order.index(builtin) + 1
        continue
      else:
        # If section present, insert into order at logical index.
        if builtin in sections:
          order.insert(section_insertion_idx, builtin)
          section_insertion_idx += 1
    if 'about' in sections and 'about' not in order:
      order.append('about')
    return order

class VimPlugin(object):
  """State for entire plugin (potentially multiple modules)."""

  def __init__(self, name):
    self.name = name
    self.collections = {}
    self.tagline = None
    self.author = None
    self.stylization = None
    self.library = None

  def ConsumeMetadata(self, block):
    assert block.locals.get('type') in [vimdoc.SECTION, vimdoc.BACKMATTER]
    # Error out for deprecated controls.
    if 'author' in block.globals:
      raise error.InvalidBlock(
          'Invalid directive @author.'
          ' Specify author field in addon-info.json instead.')
    if 'tagline' in block.globals:
      raise error.InvalidBlock(
          'Invalid directive @tagline.'
          ' Specify description field in addon-info.json instead.')
    for control in ['stylization', 'library']:
      if control in block.globals:
        if getattr(self, control) is not None:
          raise error.RedundantControl(control)
        setattr(self, control, block.globals[control])

  def LookupTag(self, typ, name):
    """Returns the tag name for the given type and name."""
    # Support both @command(Name) and @command(:Name).
    if typ == vimdoc.COMMAND:
      fullname = name.lstrip(':')
    elif typ == vimdoc.SETTING:
      scope_match = regex.setting_scope.match(name)
      fullname = scope_match and name or 'g:' + name
    else:
      fullname = name
    block = None
    if typ in self.collections:
      collection = self.collections[typ]
      candidates = [x for x in collection if x.FullName() == fullname]
      if len(candidates) > 1:
        raise KeyError('Found multiple %ss named %s' % (typ, name))
      if candidates:
        block = candidates[0]
    if block is None:
      # Create a dummy block to get default tag.
      block = Block(typ)
      block.Local(name=fullname)
    return block.TagName()

  def GetCollectionType(self, block):
    typ = block.locals.get('type')

    # The inclusion of function docs depends upon the module type.
    if typ == vimdoc.FUNCTION:
      # Exclude deprecated functions
      if block.locals.get('deprecated'):
        return None
      # If this is a library module, exclude private functions.
      if self.library and block.locals.get('private'):
        return None
      # If this is a non-library, exclude non-explicitly-public functions.
      if not self.library and block.locals.get('private', True):
        return None
      if 'exception' in block.locals:
        return vimdoc.EXCEPTION

    return typ

  def Merge(self, block):
    typ = block.locals.get('type')
    if typ in [vimdoc.SECTION, vimdoc.BACKMATTER]:
      self.ConsumeMetadata(block)
    else:
      collection_type = self.GetCollectionType(block)
      if collection_type is not None:
        self.collections.setdefault(collection_type, []).append(block)


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
      with io.open(addon_info_path, 'r', encoding='utf-8') as addon_info_file:
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
  plugin = VimPlugin(plugin_name)

  # Set module metadata from addon-info.json.
  if addon_info is not None:
    # Valid addon-info.json. Apply addon metadata.
    if 'author' in addon_info:
      plugin.author = addon_info['author']
    if 'description' in addon_info:
      plugin.tagline = addon_info['description']

  # Crawl plugin dir and collect parsed blocks for each file path.
  paths_and_blocks = []
  standalone_paths = []
  autoloaddir = os.path.join(directory, 'autoload')
  for (root, dirs, files) in os.walk(directory):
    # Visit files in a stable order, since the ordering of e.g. the Maktaba
    # flags below depends upon the order that we visit the files.
    dirs.sort()
    files.sort()

    # Prune non-standard top-level dirs like 'test'.
    if root == directory:
      dirs[:] = [x for x in dirs if x in DOC_SUBDIRS + ['after']]
    if root == os.path.join(directory, 'after'):
      dirs[:] = [x for x in dirs if x in DOC_SUBDIRS]
    for f in files:
      filename = os.path.join(root, f)
      if os.path.splitext(filename)[1] == '.vim':
        relative_path = os.path.relpath(filename, directory)
        with io.open(filename, encoding='utf-8') as filehandle:
          lines = list(filehandle)
          blocks = list(parser.ParseBlocks(lines, filename))
          # Define implicit maktaba flags for files that call
          # maktaba#plugin#Enter. These flags have to be special-cased here
          # because there aren't necessarily associated doc comment blocks and
          # the name is computed from the file name.
          if (not relative_path.startswith('autoload' + os.path.sep)
              and relative_path != os.path.join('plugin', 'flags.vim')
              and relative_path != os.path.join('instant', 'flags.vim')):
            if ContainsMaktabaPluginEnterCall(lines):
              flagpath = relative_path
              if flagpath.startswith('after' + os.path.sep):
                flagpath = os.path.relpath(flagpath, 'after')
              flagblock = Block(vimdoc.FLAG, is_default=True)
              name_parts = os.path.splitext(flagpath)[0].split(os.path.sep)
              flagname = name_parts.pop(0)
              flagname += ''.join('[' + p + ']' for p in name_parts)
              flagblock.Local(name=flagname)
              flagblock.AddLine(
                  'Configures whether {} should be loaded.'.format(
                      relative_path))
              default = 0 if flagname == 'plugin[mappings]' else 1
              # Use unbulleted list to make sure it's on its own line. Use
              # backtick to avoid helpfile syntax highlighting.
              flagblock.AddLine(' - Default: {} `'.format(default))
              blocks.append(flagblock)
        paths_and_blocks.append((relative_path, blocks))
        if filename.startswith(autoloaddir):
          if blocks and blocks[0].globals.get('standalone'):
            standalone_paths.append(relative_path)

  docdir = os.path.join(directory, 'doc')
  if not os.path.isdir(docdir):
    os.mkdir(docdir)

  modules = []

  main_module = Module(plugin_name, plugin)
  for (path, blocks) in paths_and_blocks:
    # Skip standalone paths.
    if GetMatchingStandalonePath(path, standalone_paths) is not None:
      continue
    namespace = None
    if path.startswith('autoload' + os.path.sep):
      namespace = GetAutoloadNamespace(os.path.relpath(path, 'autoload'))
    for block in blocks:
      main_module.Merge(block, namespace=namespace)
  modules.append(main_module)

  # Process standalone modules.
  standalone_modules = {}
  for (path, blocks) in paths_and_blocks:
    standalone_path = GetMatchingStandalonePath(path, standalone_paths)
    # Skip all but standalone paths.
    if standalone_path is None:
      continue
    assert path.startswith('autoload' + os.path.sep)
    namespace = GetAutoloadNamespace(os.path.relpath(path, 'autoload'))
    standalone_module = standalone_modules.get(standalone_path)
    # Initialize module if this is the first file processed from it.
    if standalone_module is None:
      standalone_module = Module(namespace.rstrip('#'), plugin)
      standalone_modules[standalone_path] = standalone_module
      modules.append(standalone_module)
    for block in blocks:
      standalone_module.Merge(block, namespace=namespace)

  for module in modules:
    module.Close()
    yield module


def GetAutoloadNamespace(filepath):
  return (os.path.splitext(filepath)[0]).replace(os.path.sep, '#') + '#'


def GetMatchingStandalonePath(path, standalones):
  for standalone in standalones:
    # Check for filename match.
    if path == standalone:
      return standalone
    # Strip off '.vim' and check for directory match.
    if path.startswith(os.path.splitext(standalone)[0] + os.path.sep):
      return standalone
  return None


def ContainsMaktabaPluginEnterCall(lines):
  """Returns whether lines of vimscript contain a maktaba#plugin#Enter call.

  Args:
    lines: A sequence of vimscript strings to search.
  """
  for _, line in parser.EnumerateStripNewlinesAndJoinContinuations(lines):
    if not parser.IsComment(line) and 'maktaba#plugin#Enter(' in line:
      return True
  return False
