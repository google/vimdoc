"""Vimdoc blocks: encapsulated chunks of documentation."""
from collections import OrderedDict
import warnings

import vimdoc
from vimdoc import error
from vimdoc import paragraph
from vimdoc import regex


class Block(object):
  """Blocks are encapsulated chunks of documentation.

  They consist of a number of paragraphs and an optional header. The paragraphs
  can come in many types, including text, lists, or code. The block may also
  contain metadata statements specifying things like the plugin author, etc.

  Args:
    type: Block type, e.g. vim.SECTION or vim.FUNCTION.
    is_secondary: Whether there are other blocks above this one that describe
        the same item. Only primary blocks should have tags, not secondary
        blocks.
    is_default: Whether other blocks with the same type and tag should override
        this one and prevent this block from showing up in the docs.
  """

  def __init__(self, type=None, is_secondary=False, is_default=False):
    # May include:
    # deprecated (boolean)
    # dict (name)
    # private (boolean, in function)
    # name (of section)
    # type (constant, e.g. vimdoc.FUNCTION)
    # id (of section, in section or backmatter)
    # parent_id (in section)
    # children (in section)
    # level (in section, tracks nesting level)
    # namespace (of function)
    # attribute (of function in dict)
    self.locals = {}
    if type is not None:
      self.SetType(type)
    # Merged into module. May include:
    # author (string)
    # library (boolean)
    # order (list of strings)
    # standalone (boolean)
    # stylization (string)
    # tagline (string)
    self.globals = {}
    self.header = None
    self.paragraphs = paragraph.Paragraphs()
    self._required_args = []
    self._optional_args = []
    self._closed = False
    self._is_secondary = is_secondary
    self._is_default = is_default

  def AddLine(self, line):
    """Adds a line of text to the block. Paragraph type is auto-determined."""
    # Code blocks are treated differently:
    # Newlines aren't joined and blanklines aren't special.
    # See :help help-writing for specification.
    if self.paragraphs.IsType(paragraph.CodeBlock):
      # '<' exits code blocks.
      if line.startswith('<'):
        self.paragraphs.Close()
        line = line[1:].lstrip()
        if line:
          self.AddLine(line)
        return
      # Lines starting in column 0 exit code lines.
      if line[:1] not in ' \t':
        self.paragraphs.Close()
        self.AddLine(line)
        return
      self.paragraphs.AddLine(line)
      return
    # Always grab the required/optional args.
    self._ParseArgs(line)
    # Blank lines divide paragraphs.
    if not line.strip():
      self.paragraphs.SetType(paragraph.BlankLine)
      return
    # Start lists if you get a list item.
    match = regex.list_item.match(line or '')
    if match:
      leader = match.group(1)
      self.paragraphs.Close()
      line = regex.list_item.sub('', line)
      self.paragraphs.SetType(paragraph.ListItem, leader)
      self.paragraphs.AddLine(line)
      return
    if line and line[:1] in ' \t':
      # Continue lists by indenting.
      if self.paragraphs.IsType(paragraph.ListItem):
        self.paragraphs.AddLine(line.lstrip())
        return
    elif self.paragraphs.IsType(paragraph.ListItem):
      self.paragraphs.Close()
    # Everything else is text.
    self.paragraphs.SetType(paragraph.TextParagraph)
    # Lines ending in '>' enter code blocks. Must have a space before if it if
    # not on a line by itself.
    if line == '>' or line.endswith(' >'):
      line = line[:-1].rstrip()
      if line:
        self.paragraphs.AddLine(line)
      self.paragraphs.SetType(paragraph.CodeBlock)
      return
    # Normal paragraph handling.
    self.paragraphs.AddLine(line)

  def Global(self, **kwargs):
    """Sets global metadata, like plugin author."""
    self.SetType(True)
    for key, value in kwargs.items():
      if key in self.globals:
        raise error.RedundantControl(key)
      self.globals[key] = value

  def Local(self, **kwargs):
    """Sets local metadata, like private/public scope."""
    self.SetType(True)
    for key, value in kwargs.items():
      if key in self.locals and self.locals[key] != value:
        raise error.InconsistentControl(key, self.locals[key], value)
      self.locals[key] = value

  def SetType(self, newtype):
    """Sets the block type (function, command, etc.)."""
    ourtype = self.locals.get('type')
    # 'True' means "I'm definitely vimdoc but I don't have a type yet".
    if newtype is True or newtype == ourtype:
      self.locals['type'] = ourtype or newtype
      return
    # 'None' means "I don't know one way or the other".
    if ourtype is None or ourtype is True:
      self.locals['type'] = newtype
    else:
      raise error.TypeConflict(ourtype, newtype)

  def SetParentSection(self, parent_id):
    """Sets the parent_id for blocks of type SECTION"""
    if not (self.locals.get('type') == vimdoc.SECTION):
      raise error.MisplacedParentSection(parent_id)
    self.Local(parent_id=parent_id)

  def SetHeader(self, directive):
    """Sets the header handler."""
    if self.header:
      raise error.MultipleErrors
    self.header = directive
    self.paragraphs.Close()

  def AddSubHeader(self, name):
    """Adds a subheader line."""
    self.paragraphs.SetType(paragraph.SubHeaderLine, name)

  def Default(self, arg, value):
    """Adds a line which sets the default value for an optional arg."""
    # If you do "@default foo=[bar]" it's implied that [bar] precedes [foo] in
    # the argument list -- hence, we parse value before arg.
    self._ParseArgs(value)
    # The arg is assumed optional, since it can default to things.
    if arg not in self._optional_args:
      self._optional_args.append(arg)
    self.paragraphs.SetType(paragraph.DefaultLine, arg, value)

  def Except(self, typ, description):
    """Adds a line specifying that the code can throw a specific exception."""
    description = description or ''
    self._ParseArgs(description)
    self.paragraphs.SetType(paragraph.ExceptionLine, typ, description)

  def Close(self):
    """Closes the block against further text.

    This triggers expansion of the header, if it exists. This must be done
    before the header can be used.

    Returns:
      The block itself, for easy chaining. (So you can yield block.Close())
    """
    if self._closed:
      return
    self._closed = True
    if self.locals.get('type') is True and 'dict' in self.locals:
      self.SetType(vimdoc.DICTIONARY)
    if (self.locals.get('type') in [vimdoc.FUNCTION, vimdoc.COMMAND]
        and 'exception' not in self.locals):
      if not self.header:
        # We import here to avoid a circular dependency.
        # pylint:disable-msg=g-import-not-at-top
        from vimdoc.docline import Usage
        self.header = Usage('{]')
      self.locals['usage'] = self.header.GenerateUsage(self)
    if 'private' in self.locals and self.locals.get('type') != vimdoc.FUNCTION:
      raise error.InvalidBlock('Only functions may be marked as private.')
    return self

  def RequiredArgs(self):
    """Gets a list of arguments required by the block."""
    if self.locals.get('type') == vimdoc.FUNCTION:
      sigargs = [a for a in self.locals.get('args') if a != '...']
      # They didn't mention any args. Use the args from the function signature.
      if not self._required_args:
        return sigargs
      # The args they did mention are all in the signature. Use the argument
      # order from the function signature.
      if not set(self._required_args).difference(sigargs):
        return sigargs
      # Looks like they're renaming the signature's args. Use the arguments that
      # they named in the order they named them.
      if len(self._required_args) == len(sigargs):
        return self._required_args
      # We have no idea what they're doing. The function signature doesn't match
      # the arguments mentioned in the documentation.
      warnings.warn(
          'Arguments do not match function signature. '
          'Function signature arguments are {}. '
          'Documentation arguments are {}.'
          .format(sigargs, self._required_args),
          error.ArgumentMismatch)
    return self._required_args

  def OptionalArgs(self):
    """Gets a list of optional arguments accepted by the doc'd code."""
    if (self.locals.get('type') == vimdoc.FUNCTION
        and self._optional_args
        and '...' not in self.locals.get('args')):
      # The function accepts no optional parameters. Warn and return nothing.
      warnings.warn(
          'Documentation claims optional parameters '
          'that function {} does not accept.'.format(self.FullName()),
          error.DocumentationWarning)
      return ()
    return self._optional_args

  def LocalName(self):
    """The (file-)local name of the doc'd code element."""
    if self.locals.get('type') == vimdoc.DICTIONARY:
      return self.locals['dict']
    if 'name' not in self.locals:
      raise KeyError('Unnamed block.')
    return self.locals['name']

  def FullName(self):
    """The global (namespaced as necessary) name of the code element."""
    typ = self.locals.get('type')
    if typ == vimdoc.FUNCTION:
      if 'dict' in self.locals:
        attribute = self.locals.get('attribute', self.LocalName())
        return '{}.{}'.format(self.locals['dict'], attribute)
      if 'exception' in self.locals:
        return 'ERROR({})'.format(self.locals['exception'] or self.LocalName())
      return self.locals.get('namespace', '') + self.LocalName()
    return self.LocalName()

  def TagName(self):
    """The tag string to use for links to the code element."""
    if self._is_secondary:
      return None
    typ = self.locals.get('type')
    if typ == vimdoc.FUNCTION:
      # Function tags end with (), except for the special case of ERROR() tags.
      if 'exception' not in self.locals:
        return '{}()'.format(self.FullName())
    if typ == vimdoc.COMMAND:
      return ':{}'.format(self.FullName())
    return self.FullName()

  def IsDefault(self):
    """Whether this block is a default only as opposed to an explicit block."""
    return self._is_default

  def _ParseArgs(self, args):
    # Removes duplicates but retains order:
    self._required_args = list(OrderedDict.fromkeys(
        self._required_args + regex.required_arg.findall(args)))
    self._optional_args = list(OrderedDict.fromkeys(
        self._optional_args + regex.optional_arg.findall(args)))

  def __repr__(self):
    try:
      name = self.FullName()
    except KeyError:
      name = '?'
    return '{}({})'.format(self.__class__.__name__, name)

  def __lt__(self, other):
    return self.FullName() < other.FullName()
