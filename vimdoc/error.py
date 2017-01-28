"""Vimdoc error classes."""


class Error(Exception):
  pass


class DocumentationWarning(Warning):
  pass


class InvalidAddonInfo(Warning):
  pass


class ParseError(Error):
  def __init__(self, message, filename=None, lineno=None):
    self.filename = filename
    self.lineno = lineno
    super(ParseError, self).__init__(message)

  def __str__(self):
    parent = super(ParseError, self).__str__()
    if self.lineno is not None or self.filename is not None:
      lineno = '???' if self.lineno is None else ('%03d' % self.lineno)
      filename = '???' if self.filename is None else self.filename
      prefix = '{}.{}: '.format(filename, lineno)
    else:
      prefix = ''
    return prefix + parent


class ArgumentMismatch(Warning):
  pass


class TypeConflict(ParseError):
  def __init__(self, t1, t2, *args, **kwargs):
    super(TypeConflict, self).__init__(
        'Type {} is incompatible with type {}'.format(t1, t2),
        *args, **kwargs)


class InvalidBlockNumber(ParseError):
  def __init__(self, number, blocks, selection, *args, **kwargs):
    super(InvalidBlockNumber, self).__init__(
        'There is no block number {}. '
        'There are {} blocks. '
        'Current selection is {}'
        .format(number, len(blocks), selection),
        *args, **kwargs)


class InvalidBlockArgs(ParseError):
  def __init__(self, block, params, *args, **kwargs):
    super(InvalidBlockArgs, self).__init__(
        'Invalid args for block {}: "{}"'.format(block, params),
        *args, **kwargs)


class UnrecognizedBlockDirective(ParseError):
  def __init__(self, block, *args, **kwargs):
    super(UnrecognizedBlockDirective, self).__init__(
        'Unrecognized block directive "{}"'.format(block), *args, **kwargs)


class UnrecognizedInlineDirective(ParseError):
  def __init__(self, inline, *args, **kwargs):
    super(UnrecognizedInlineDirective, self).__init__(
        'Unrecognized inline directive "%s"' % inline, *args, **kwargs)


class CannotContinue(ParseError):
  pass


class RedundantControl(ParseError):
  def __init__(self, control, *args, **kwargs):
    super(RedundantControl, self).__init__(
        'Redundant control "{}"'.format(control),
        *args, **kwargs)


class InconsistentControl(ParseError):
  def __init__(self, control, old, new, *args, **kwargs):
    super(InconsistentControl, self).__init__(
        'Inconsistent control "{}" ({} vs {})'.format(control, old, new),
        *args, **kwargs)


class MultipleHeaders(ParseError):
  def __init__(self, *args, **kwargs):
    super(MultipleHeaders, self).__init__(
        'Block given multiple headers.',
        *args, **kwargs)


class InvalidBlock(ParseError):
  pass


class AmbiguousBlock(ParseError):
  def __init__(self, *args, **kwargs):
    super(AmbiguousBlock, self).__init__(
        'Block type is ambiguous.',
        *args, **kwargs)


class BadStructure(Error):
  pass


class NoSuchSection(BadStructure):
  def __init__(self, section):
    super(NoSuchSection, self).__init__(
        'Section {} never defined.'.format(section))


class MisplacedParentSection(BadStructure):
  def __init__(self, section):
    super(MisplacedParentSection, self).__init__(
        'Parent section {} defined outside a @section block.'.format(section))


class NoSuchParentSection(BadStructure):
  def __init__(self, section, parent_id):
    super(NoSuchParentSection, self).__init__(
        ('Section {} has non-existent parent {}. '
         'Try setting the id of the parent section explicitly.'
        ).format(section, parent_id))


class DuplicateSection(BadStructure):
  def __init__(self, section):
    super(DuplicateSection, self).__init__(
        'Duplicate section {} defined.'.format(section))


class DuplicateBackmatter(BadStructure):
  def __init__(self, section):
    super(DuplicateBackmatter, self).__init__(
        'Duplicate backmatter defined for section {}.'.format(section))


class NeglectedSections(BadStructure):
  def __init__(self, sections, order):
    super(NeglectedSections, self).__init__(
        'Sections {} not included in ordering {}.'.format(sections, order))


class OrderedChildSections(BadStructure):
  def __init__(self, section, order):
    super(OrderedChildSections, self).__init__(
        'Child section {} included in ordering {}.'.format(section, order))
