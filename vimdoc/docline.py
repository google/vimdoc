"""Vimfile documentation lines, the stuff of vimdoc blocks."""
import abc

import vimdoc
from vimdoc import error
from vimdoc import regex
from vimdoc.block import Block


class DocLine(object):
  """One line of vim documentation."""

  __metaclass__ = abc.ABCMeta

  def Each(self, blocks, selection):
    """Iterates the selected blocks."""
    for i in selection:
      if i >= len(blocks):
        raise error.InvalidBlockNumber(i, blocks, selection)
      yield blocks[i]

  def Affect(self, blocks, selection):
    """Updates each selected block.

    Args:
      blocks: The different blocks defined so far.
      selection: The blocks being operated upon.
    Returns:
      The blocks ready to be closed (which is an empty list -- codelines are the
      ones who close blocks, not doclines.)
    """
    if not blocks:
      blocks.append(Block())
      selection.append(0)
    for block in self.Each(blocks, selection):
      self.Update(block)
    return ()

  @abc.abstractmethod
  def Update(self, block):
    """Update one block."""


class Text(DocLine):
  def __init__(self, line):
    self.line = line

  def Update(self, block):
    block.AddLine(self.line)


class BlockDirective(DocLine):
  """A line-spanning directive, like @usage."""

  __metaclass__ = abc.ABCMeta

  REGEX = regex.no_args

  def __init__(self, args):
    match = self.REGEX.match(args)
    if not match:
      raise error.InvalidBlockArgs(self.__class__.__name__, args)
    self.Assign(*match.groups())

  def Assign(self):
    pass


class All(BlockDirective):
  REGEX = regex.no_args

  def Assign(self):
    pass

  def Affect(self, blocks, selection):
    selection[:] = range(len(blocks))
    for block in blocks:
      block.SetType(True)
    return ()

  def Update(self, block):
    pass


class Author(BlockDirective):
  REGEX = regex.any_args

  def Assign(self, author):
    self.author = author

  def Update(self, block):
    block.Global(author=self.author)


class Backmatter(BlockDirective):
  REGEX = regex.backmatter_args

  def Assign(self, ident):
    self.id = ident

  def Update(self, block):
    block.SetType(vimdoc.BACKMATTER)
    block.Local(id=self.id)


class Default(BlockDirective):
  REGEX = regex.default_args

  def Assign(self, arg, value):
    self.arg = arg
    self.value = value

  def Update(self, block):
    block.Default(self.arg, self.value)


class Deprecated(BlockDirective):
  REGEX = regex.one_arg

  def Assign(self, reason):
    self.reason = reason

  def Update(self, block):
    block.Local(deprecated=self.reason)


# pylint: disable=g-bad-name
class Exception_(BlockDirective):
  REGEX = regex.maybe_word

  def Assign(self, word):
    self.word = word

  def Update(self, block):
    block.Local(exception=self.word)


class Dict(BlockDirective):
  REGEX = regex.dict_args

  def Assign(self, name, attribute=None):
    self.name = name
    self.attribute = attribute

  def Update(self, block):
    block.SetType(True)
    block.Local(dict=self.name)
    if self.attribute:
      block.SetType(vimdoc.FUNCTION)
      block.Local(attribute=self.attribute)
    # We can't set the dict type here because it may be set to Function type
    # later, and we don't want a type mismatch.


class Library(BlockDirective):
  def Update(self, block):
    block.Global(library=True)


class Order(BlockDirective):
  REGEX = regex.order_args

  def Assign(self, args):
    self.order = regex.order_arg.findall(args)

  def Update(self, block):
    block.Global(order=self.order)


class Private(BlockDirective):
  def Update(self, block):
    block.Local(private=True)


class Public(BlockDirective):
  def Update(self, block):
    block.Local(private=False)


class Section(BlockDirective):
  REGEX = regex.section_args

  def __init__(self, args):
    super(Section, self).__init__(args)

  def Assign(self, name, ident):
    self.name = name.replace('\\,', ',').replace('\\\\', '\\')

    if ident is None:
      # If omitted, it's the name in lowercase, with spaces converted to dashes.
      ident = self.name.lower().replace(' ', '-')
    self.id = ident

  def Update(self, block):
    block.SetType(vimdoc.SECTION)
    block.Local(name=self.name, id=self.id)


class ParentSection(BlockDirective):
  REGEX = regex.parent_section_args

  def Assign(self, name):
    self.name = name.lower()

  def Update(self, block):
    block.SetParentSection(self.name)


class Setting(BlockDirective):
  REGEX = regex.one_arg

  def Assign(self, name):
    scope_match = regex.setting_scope.match(name)
    # Assume global scope if no explicit scope given.
    if scope_match is None:
      name = 'g:' + name
    self.name = name

  def Update(self, block):
    block.SetType(vimdoc.SETTING)
    block.Local(name=self.name)


class Standalone(BlockDirective):
  def Update(self, block):
    block.Global(standalone=True)


class Stylized(BlockDirective):
  REGEX = regex.stylizing_args

  def Assign(self, stylization):
    self.stylization = stylization

  def Update(self, block):
    block.Global(stylization=self.stylization)


class SubSection(BlockDirective):
  REGEX = regex.any_args

  def Assign(self, name):
    self.name = name

  def Update(self, block):
    block.AddSubHeader(self.name)


class Tagline(BlockDirective):
  REGEX = regex.any_args

  def Assign(self, tagline):
    self.tagline = tagline

  def Update(self, block):
    block.Global(tagline=self.tagline)


class Throws(BlockDirective):
  REGEX = regex.throw_args

  def Assign(self, typ, description):
    if not regex.vim_error.match(typ):
      typ = 'ERROR({})'.format(typ)
    self.error = typ
    self.description = description

  def Update(self, block):
    block.Except(self.error, self.description)


class Header(BlockDirective):
  """A header directive, like @usage @function or @command."""

  __metaclass__ = abc.ABCMeta

  def Affect(self, blocks, selection):
    """Updates the block selection.

    If this block is already split into multiple sections, or if it already has
    a header, then a new section is created with this header. Otherwise, this
    header is set as the header for the single block.

    Args:
      blocks: The blocks defined in the documentation so far.
      selection: The blocks currently being acted on.
    Returns:
      The blocks ready to be closed (which is none).
    """
    if (len(blocks) != 1) or (blocks[0].header):
      # Mark this as a secondary block if there are other blocks above it that
      # are describing the same block. (This allows us to, for example, only add
      # the function tag to the FIRST block that describes the function and not
      # to subsequent blocks showing other ways to use the same function.)
      is_secondary = len(blocks) > 0
      newblock = Block(is_secondary=is_secondary)
      # If the first block has no header, copy its locals.
      if blocks and blocks[0].header is None:
        newblock.locals = dict(blocks[0].locals)
      blocks.append(newblock)
      selection[:] = [len(blocks) - 1]
    else:
      # There is only one block. Assert that it's selected.
      assert selection == [0], 'Singleton blocks must be selected.'
    for block in self.Each(blocks, selection):
      block.SetHeader(self)
      self.Update(block)
    return ()

  def Assign(self, usage):
    self.usage = usage
    self.reqs = regex.required_arg.findall(usage)
    self.opts = regex.optional_arg.findall(usage)

  def Update(self, block):
    pass

  def GenerateUsage(self, block):
    isfunc = block.locals.get('type') == vimdoc.FUNCTION
    sep = ', ' if isfunc else ' '
    extra_reqs = sep.join('{%s}' % r
                          for r in block.RequiredArgs()
                          if r not in self.reqs)
    extra_opts = sep.join('[%s]' % o
                          for o in block.OptionalArgs()
                          if o not in self.opts)
    usage = self.FillOut(block.FullName(), sep, extra_reqs, extra_opts)
    # Command usage should have a ':' prefix before the name.
    if block.locals.get('type') == vimdoc.COMMAND and not usage.startswith(':'):
      usage = ':' + usage
    return usage

  def FillOut(self, name, sep, extra_reqs, extra_opts):
    """Expands the usage line with the given arguments."""
    # The user may use the {] hole to place both required and optional args,
    # appropriately separated.
    if extra_reqs and extra_opts:
      extra_args = extra_reqs + sep + extra_opts
    else:
      extra_args = extra_reqs + extra_opts
    # Expand the argument holes.
    # Presumably, the user won't use both the arg hole and the required/optional
    # holes. If they do, then we'll dutifully replicate the args.
    usage = regex.arg_hole.sub(extra_args, self.usage)
    usage = regex.required_hole.sub(extra_reqs, usage)
    usage = regex.optional_hole.sub(extra_opts, usage)
    # Remove bad separators.
    usage = regex.bad_separator.sub('', usage)
    # Expand the name holes.
    usage = regex.name_hole.sub(name, usage)
    # Expand the hole escape sequences.
    usage = regex.namehole_escape.sub(r'<\1>', usage)
    usage = regex.requiredhole_escape.sub(r'{\1}', usage)
    usage = regex.optionalhole_escape.sub(r'[\1]', usage)
    return usage


class Command(Header):
  REGEX = regex.any_args

  def Update(self, block):
    block.SetType(vimdoc.COMMAND)


class Function(Header):
  REGEX = regex.any_args

  def Update(self, block):
    block.SetType(vimdoc.FUNCTION)


class Usage(Header):
  REGEX = regex.usage_args

  def GenerateUsage(self, block):
    """Generates the usage line. Syntax depends upon the block type."""
    normalize = lambda arg: arg if arg[0] in '[{' else ('{%s}' % arg)
    args = [normalize(arg) for arg in regex.usage_arg.findall(self.usage)]
    if block.locals.get('type') == vimdoc.FUNCTION:
      # Functions are like MyFunction({req1}, {req2}, [opt1])
      self.usage = '<>(%s)' % ', '.join(args)
    else:
      assert block.locals.get('type') == vimdoc.COMMAND
      # Commands are like :[range]MyCommand[!] {req1} {req2} [opt1]
      self.usage = ':%s %s' % (block.locals.get('head', '<>'), ' '.join(args))
    return super(Usage, self).GenerateUsage(block)


BLOCK_DIRECTIVES = {
    'all': All,
    'author': Author,
    'backmatter': Backmatter,
    'command': Command,
    'default': Default,
    'deprecated': Deprecated,
    'dict': Dict,
    'exception': Exception_,
    'function': Function,
    'library': Library,
    'order': Order,
    'parentsection': ParentSection,
    'private': Private,
    'public': Public,
    'section': Section,
    'setting': Setting,
    'standalone': Standalone,
    'stylized': Stylized,
    'subsection': SubSection,
    'tagline': Tagline,
    'throws': Throws,
    'usage': Usage,
}
