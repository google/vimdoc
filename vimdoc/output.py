"""Vim helpfile outputter."""
import io
import os
import textwrap

import vimdoc
from vimdoc import error
from vimdoc import paragraph
from vimdoc import regex


class Helpfile(object):
  """Outputs vim help files."""

  WIDTH = 78
  TAB = '  '

  def __init__(self, module, docdir):
    self.module = module
    self.docdir = docdir

  def Filename(self):
    help_filename = self.module.name.replace('#', '-')
    return help_filename + '.txt'

  def Write(self):
    filename = os.path.join(self.docdir, self.Filename())
    # Output POSIX line endings for portable output that can be published.
    # They are displayed properly in vim on all platforms.
    with io.open(filename, 'w', encoding='utf-8', newline='\n') as self.file:
      self.WriteHeader()
      self.WriteTableOfContents()
      for chunk in self.module.Chunks():
        self.WriteChunk(chunk)
      self.WriteFooter()

  def WriteHeader(self):
    """Writes a plugin header."""
    # The first line should conform to ':help write-local-help', with a tag for
    # the filename followed by a tab and the tagline (if present). Line 1 will
    # not be wrapped at WIDTH since the first line has special semantics.
    line = self.Tag(self.Filename())
    if self.module.plugin.tagline:
      line = '{}\t{}'.format(line, self.module.plugin.tagline)
    # Use Print directly vs. WriteLine so tab isn't expanded by TextWrapper, and
    # to bypass line wrapping at WIDTH.
    self.Print(line, wide=True)
    # Next write a line with the author (if present) and tags.
    tag = self.Tag(self.module.name)
    if self.module.plugin.stylization:
      tag = '{} {}'.format(self.Tag(self.module.plugin.stylization), tag)
    if self.module.plugin.author:
      self.WriteLine(self.module.plugin.author, right=tag)
    else:
      self.WriteLine(right=tag)
    self.WriteLine()

  # Helper function for WriteTableOfContents().
  def _EnumerateIndices(self, sections):
    """Keep track of section numbering for each level of the tree"""
    count = [{'level': 0, 'index': 0}]
    for block in sections:
      assert 'id' in block.locals
      assert 'name' in block.locals
      level = block.locals['level']
      while level < count[-1]['level']:
        count.pop()
      if level == count[-1]['level']:
        count[-1]['index'] += 1
      else:
        count.append({'level': level, 'index': 1})
      yield (count[-1]['index'], block)

  def WriteTableOfContents(self):
    """Writes the table of contents."""
    self.WriteRow()
    self.WriteLine('CONTENTS', right=self.Tag(self.Slug('contents')))
    # We need to keep track of section numbering on a per-level basis
    for index, block in self._EnumerateIndices(self.module.sections.values()):
      self.WriteLine(
          '%d. %s' % (index, block.locals['name']),
          indent=2 * block.locals['level'] + 1,
          right=self.Link(self.Slug(block.locals['id'])),
          fill='.')
    self.WriteLine()

  def WriteChunk(self, chunk):
    """Writes one vimdoc Block."""
    assert 'type' in chunk.locals
    typ = chunk.locals['type']
    if typ == vimdoc.SECTION:
      self.WriteSection(chunk)
    elif typ == vimdoc.FUNCTION:
      if 'exception' in chunk.locals:
        self.WriteSmallBlock(chunk.FullName(), chunk)
      else:
        self.WriteLargeBlock(chunk)
    elif typ == vimdoc.COMMAND:
      self.WriteLargeBlock(chunk)
    elif typ == vimdoc.SETTING:
      self.WriteSmallBlock(chunk.FullName(), chunk)
    elif typ == vimdoc.FLAG:
      self.WriteSmallBlock(self.Slug(chunk.FullName(), ':'), chunk)
    elif typ == vimdoc.DICTIONARY:
      self.WriteSmallBlock(self.Slug(chunk.FullName(), '.'), chunk)
    elif typ == vimdoc.BACKMATTER:
      self.WriteParagraphs(chunk)

  def WriteSection(self, block):
    """Writes a section-type block."""
    self.WriteRow()
    name = block.locals['name']
    ident = block.locals['id']
    slug = self.Slug(ident)
    self.WriteLine(name.upper(), right=self.Tag(slug))
    if block.paragraphs:
      self.WriteLine()
    self.WriteParagraphs(block)

  def WriteLargeBlock(self, block):
    """Writes a large (function, command, etc.) type block."""
    assert 'usage' in block.locals
    self.WriteLine(
        # The leader='' makes it indent once on subsequent lines.
        block.locals['usage'], right=self.Tag(block.TagName()), leader='')
    self.WriteParagraphs(block, indent=1)

  def WriteSmallBlock(self, slug, block):
    """Writes a small (flag, setting, etc.) type block."""
    self.WriteLine(right=self.Tag(slug))
    self.WriteParagraphs(block)

  def WriteFooter(self):
    """Writes a plugin footer."""
    self.WriteLine()
    self.WriteLine('vim:tw={}:ts=8:ft=help:norl:'.format(self.WIDTH))

  def WriteParagraphs(self, block, indent=0):
    """Writes a series of text with optional indents."""
    assert 'namespace' in block.locals
    for p in block.paragraphs:
      self.WriteParagraph(p, block.locals['namespace'], indent=indent)
    self.WriteLine()

  def WriteParagraph(self, p, namespace, indent=0):
    """Writes one paragraph."""
    if isinstance(p, paragraph.ListItem):
      # - indents lines after the first
      if p.leader == '-':
        leader = ''
      # + indents the whole paragraph
      elif p.leader == '+':
        leader = '  '
      # Other leaders (*, 1., etc.) are copied verbatim, indented by one
      # shiftwidth.
      else:
        leader = p.leader + ' '
        indent += 1
      self.WriteLine(self.Expand(
          p.text, namespace), indent=indent, leader=leader)
    elif isinstance(p, paragraph.TextParagraph):
      self.WriteLine(self.Expand(p.text, namespace), indent=indent)
    elif isinstance(p, paragraph.BlankLine):
      self.WriteLine()
    elif isinstance(p, paragraph.CodeBlock):
      self.WriteLine('>')
      for line in p.lines:
        self.WriteCodeLine(line, namespace, indent=indent)
      self.WriteLine('<')
    elif isinstance(p, paragraph.DefaultLine):
      self.WriteLine(self.Default(
          p.arg, p.value, namespace), indent=indent)
    elif isinstance(p, paragraph.ExceptionLine):
      self.WriteLine(self.Throws(
          p.exception, p.description, namespace), indent=indent)
    elif isinstance(p, paragraph.SubHeaderLine):
      self.WriteLine(p.name.upper(), indent=indent)
    else:
      raise ValueError('What kind of paragraph is {}?'.format(p))

  def WriteCodeLine(self, text, namespace, indent=0):
    """Writes one line of code."""
    wrapper = textwrap.TextWrapper(
        width=self.WIDTH,
        initial_indent=(indent * self.TAB),
        subsequent_indent=((indent + 2) * self.TAB))
    # wrap returns empty list for ''. See http://bugs.python.org/issue15510.
    lines = wrapper.wrap(self.Expand(text, namespace)) or ['']
    for line in lines:
      self.Print(line)

  def Print(self, line, end='\n', wide=False):
    """Outputs a line to the file."""
    if not wide:
      assert len(line) <= self.WIDTH
    if self.file is None:
      raise ValueError('Helpfile writer not yet given helpfile to write.')
    self.file.write(line + end)

  def WriteRow(self):
    """Writes a horizontal divider row."""
    self.Print('=' * self.WIDTH)

  def WriteLine(self, text='', right='', indent=0, leader=None, fill=' '):
    """Writes one line of output, breaking it up as needed."""
    if leader is not None:
      initial_indent = (indent * self.TAB) + leader
      subsequent_indent = (indent + 1) * self.TAB
    else:
      initial_indent = indent * self.TAB
      subsequent_indent = indent * self.TAB
    wrapper = textwrap.TextWrapper(
        width=self.WIDTH,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_on_hyphens=False)
    lines = wrapper.wrap(text)
    # wrap returns empty list for ''. See http://bugs.python.org/issue15510.
    lines = lines or ['']
    lastlen = len(lines[-1])
    rightlen = len(right)
    assert rightlen <= self.WIDTH
    if right and lastlen + rightlen + 1 > self.WIDTH:
      lines.append('')
      lastlen = 0
    if right:
      padding = self.WIDTH - lastlen - rightlen
      assert padding >= 0
      lines[-1] += (fill * padding) + right
    for line in lines:
      self.Print(line)

  def Slug(self, slug, sep='-'):
    return '{}{}{}'.format(self.module.name, sep, slug)

  def Tag(self, slug):
    return '' if slug is None else '*{}*'.format(slug)

  def Link(self, slug):
    return '|{}|'.format(slug)

  def Throws(self, err, description, namespace):
    return 'Throws {} {}'.format(err, self.Expand(description, namespace))

  def Default(self, arg, value, namespace):
    return '[{}] is {} if omitted.'.format(arg, self.Expand(value, namespace))

  def Expand(self, text, namespace):
    def Expander(match):
      expanded = self.ExpandInline(*match.groups(), namespace=namespace)
      if expanded is None:
        # Leave unrecognized directives unexpanded. Might be false positives.
        return match.group(0)
      return expanded
    return regex.inline_directive.sub(Expander, text)

  def ExpandInline(self, inline, element, namespace):
    """Expands inline directives, like @function()."""
    if inline == 'section':
      return self.Link(self.Slug(element))
    elif inline == 'function':
      # If a user says @function(#Foo) then that points to in#this#file#Foo.
      if element.startswith('#'):
        element = (namespace or '') + element[1:]
      return self.Link(self.module.LookupTag(vimdoc.FUNCTION, element))
    elif inline == 'command':
      return self.Link(self.module.LookupTag(vimdoc.COMMAND, element))
    elif inline == 'flag':
      return self.Link(
          self.Slug(self.module.LookupTag(vimdoc.FLAG, element), ':'))
    elif inline == 'setting':
      return self.Link(self.module.LookupTag(vimdoc.SETTING, element))
    elif inline == 'dict':
      return self.Link(self.Slug(self.module.LookupTag(
          vimdoc.DICTIONARY, element), '.'))
    elif inline == 'plugin':
      if element == 'author':
        return self.module.plugin.author
      elif element == 'stylized':
        return self.module.plugin.stylization
      elif element == 'name':
        return self.module.name
      elif element is None:
        return self.module.plugin.stylization
      else:
        raise error.UnrecognizedInlineDirective(
            '{} attribute in {}'.format(element, inline))
    return None
