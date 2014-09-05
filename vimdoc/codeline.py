"""Parse vim code to mutate vimdoc blocks."""
import abc

import vimdoc
import vimdoc.block


class CodeLine(object):
  """A line of code that affects the block above it.

  For example, the documentation above a function line will be modified to set
  type=FUNCTION.
  """
  __metaclass__ = abc.ABCMeta

  def Update(self, block):
    """Updates a single block."""

  def Affect(self, blocks, selection):
    """Affects all blocks above the code line.

    There can be multiple blocks above the code line, for example:

    " @usage item index list
    " Insert {item} at {list} after {index}
    " @usage value key dict
    " Insert {value} in {dict} under {key}
    function ...

    All blocks will be affected, regardless of selection. Then all blocks will
    be unselected: once the documentation hits the codeline, the blocks are
    done.

    Args:
      blocks: The blocks above this codeline.
      selection: the selected blocks.

    Yields:
        Each block after updating it.
    """
    for block in blocks:
      self.Update(block)
      yield block
    blocks[:] = []
    selection[:] = []


class Blank(CodeLine):
  """A blank line."""


class EndOfFile(CodeLine):
  """The end of the file."""


class Unrecognized(CodeLine):
  """A code line that doesn't deserve decoration."""

  def __init__(self, line):
    self.line = line

  def Affect(self, blocks, selection):
    """Documentation above unrecognized lines is ignored."""
    blocks[:] = []
    selection[:] = []
    return ()


class Definition(CodeLine):
  """An abstract definition line."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, typ, name):
    self.name = name
    self.type = typ

  def Update(self, block):
    block.SetType(self.type)
    block.Local(name=self.name)


class Function(Definition):
  """Function definition."""

  def __init__(self, name, namespace, args):
    self.name = name
    self.namespace = namespace
    self.args = args
    super(Function, self).__init__(vimdoc.FUNCTION, name)

  def Update(self, block):
    super(Function, self).Update(block)
    if self.namespace:
      block.Local(namespace=self.namespace, local=True, args=self.args)
    else:
      block.Local(local=False, args=self.args)


class Command(Definition):
  """Command definition."""

  def __init__(self, name, **flags):
    self.flags = flags
    super(Command, self).__init__(vimdoc.COMMAND, name)

  def Update(self, block):
    """Updates one block above the command line."""
    super(Command, self).Update(block)
    # Usage is like:
    # [range][count]["x][N]MyCommand[!] {req1} {req2} [optional1] [optional2]
    head = ''
    if self.flags.get('range'):
      head += '[range]'
    if self.flags.get('count'):
      head += '[count]'
    if self.flags.get('register'):
      head += '["x]'
    if self.flags.get('buffer'):
      head += '[N]'
    head += '<>'
    if self.flags.get('bang'):
      head += '[!]'
    block.Local(head=head)


class Setting(Definition):
  def __init__(self, name):
    super(Setting, self).__init__(vimdoc.SETTING, name)


class Flag(Definition):
  def __init__(self, name, default):
    super(Flag, self).__init__(vimdoc.FLAG, name)
    self._default = default

  def Affect(self, blocks, selection):
    # Add line to show expression for default value. Can be None if vimdoc
    # failed to parse a default, e.g. due to deeply-nested parentheses.
    if self._default is not None:
      # Append to last block, creating one if there isn't one yet.
      if not blocks:
        blocks.append(vimdoc.block.Block())
      # Use unbulleted list to make sure it's on its own line. Use backtick to
      # avoid helpfile syntax highlighting.
      blocks[-1].AddLine(' - Default: {} `'.format(self._default))
    return super(Flag, self).Affect(blocks, selection)
