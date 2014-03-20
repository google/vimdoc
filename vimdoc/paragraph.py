"""Docline aggregation handlers."""
import abc


class Paragraph(object):
  """Aggregates doclines into paragraph objects.

  It's necessary to know where paragraphs start and end so that we can reflow
  text without joining too many lines. Consider:

    some text that wraps and should all
    be joined into one line
    1. must be distinguished from list items
       which must not be joined with previous lines.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self):
    self.open = True

  def Close(self):
    self.open = False

  # It's an abstract base class, pylint.
  # pylint:disable-msg=unused-argument
  def AddLine(self, text):
    if not self.open:
      raise ValueError("Can't add to closed paragraphs.")


class TextParagraph(Paragraph):
  def __init__(self):
    super(TextParagraph, self).__init__()
    self.text = ''

  def AddLine(self, text):
    super(TextParagraph, self).AddLine(text)
    if self.text:
      self.text += ' ' + text
    else:
      self.text = text


class BlankLine(Paragraph):
  def __init__(self):
    super(BlankLine, self).__init__()
    self.Close()


class CodeBlock(Paragraph):
  def __init__(self):
    super(CodeBlock, self).__init__()
    self.lines = []

  def AddLine(self, text):
    super(CodeBlock, self).AddLine(text)
    self.lines.append(text)


class DefaultLine(Paragraph):
  def __init__(self, arg, value):
    super(DefaultLine, self).__init__()
    self.open = False
    self.arg = arg
    self.value = value


class ListItem(TextParagraph):
  def __init__(self, leader='*', level=0):
    super(ListItem, self).__init__()
    self.leader = leader
    self.level = level


class ExceptionLine(Paragraph):
  def __init__(self, exception, description):
    super(ExceptionLine, self).__init__()
    self.open = False
    self.exception = exception
    self.description = description


class SubHeaderLine(Paragraph):
  def __init__(self, name):
    super(SubHeaderLine, self).__init__()
    self.open = False
    self.name = name


class Paragraphs(list):
  """A manager for many paragraphs.

  When given a line of text (with an attached type), the Paragraphs object
  decides whether to append it to the current paragraph or start a new paragraph
  (usually by checking if the types match).
  """

  def __init__(self):
    super(Paragraphs, self).__init__()

  def SetType(self, cls, *args):
    if not self.IsType(cls):
      self.append(cls(*args))

  def IsType(self, cls):
    return self and self[-1].open and isinstance(self[-1], cls)

  def AddLine(self, *args):
    # Lines are text by default.
    if not (self and self[-1].open):
      raise ValueError("Paragraph manager doesn't have an open paragraph.")
    self[-1].AddLine(*args)

  def Close(self):
    if self:
      self[-1].Close()
