"""The vimdoc parser."""
from vimdoc import codeline
from vimdoc import docline

from vimdoc import error
from vimdoc import regex


def IsComment(line):
  return regex.comment_leader.match(line)


def IsContinuation(line):
  return regex.line_continuation.match(line)


def StripContinuator(line):
  assert regex.line_continuation.match(line)
  return regex.line_continuation.sub('', line)


def EnumerateStripNewlinesAndJoinContinuations(lines):
  """Preprocesses the lines of a vimscript file.

  Enumerates the lines, strips the newlines from the end, and joins the
  continuations.

  Args:
    lines: The lines of the file.
  Yields:
    Each preprocessed line.
  """
  lineno, cached = (None, None)
  for i, line in enumerate(lines):
    line = line.rstrip('\n')
    if IsContinuation(line):
      if cached is None:
        raise error.CannotContinue('No preceding line.', i)
      elif IsComment(cached) and not IsComment(line):
        raise error.CannotContinue('No comment to continue.', i)
      else:
        cached += StripContinuator(line)
      continue
    if cached is not None:
      yield lineno, cached
    lineno, cached = (i, line)
  if cached is not None:
    yield lineno, cached


def EnumerateParsedLines(lines):
  vimdoc_mode = False
  for i, line in EnumerateStripNewlinesAndJoinContinuations(lines):
    if not vimdoc_mode:
      if regex.vimdoc_leader.match(line):
        vimdoc_mode = True
        # There's no need to yield the blank line if it's an empty starter line.
        # For example, in:
        # ""
        # " @usage whatever
        # " description
        # There's no need to yield the first docline as a blank.
        if not regex.empty_vimdoc_leader.match(line):
          # A starter line starts with two comment leaders.
          # If we strip one of them it's a normal comment line.
          yield i, ParseCommentLine(regex.comment_leader.sub('', line))
    elif IsComment(line):
      yield i, ParseCommentLine(line)
    else:
      vimdoc_mode = False
      yield i, ParseCodeLine(line)


def ParseCodeLine(line):
  """Parses one line of code and creates the appropriate CodeLine."""
  if regex.blank_code_line.match(line):
    return codeline.Blank()
  fmatch = regex.function_line.match(line)
  if fmatch:
    namespace, name, args = fmatch.groups()
    return codeline.Function(name, namespace, regex.function_arg.findall(args))
  cmatch = regex.command_line.match(line)
  if cmatch:
    args, name = cmatch.groups()
    flags = {
        'bang': '-bang' in args,
        'range': '-range' in args,
        'count': '-count' in args,
        'register': '-register' in args,
        'buffer': '-buffer' in args,
        'bar': '-bar' in args,
    }
    return codeline.Command(name, **flags)
  smatch = regex.setting_line.match(line)
  if smatch:
    name, = smatch.groups()
    return codeline.Setting('g:' + name)
  flagmatch = regex.flag_line.match(line)
  if flagmatch:
    a, b, default = flagmatch.groups()
    return codeline.Flag(a or b, default)
  return codeline.Unrecognized(line)


def ParseCommentLine(line):
  """Parses one line of documentation and creates the appropriate DocLine."""
  block = regex.block_directive.match(line)
  if block:
    return ParseBlockDirective(*block.groups())
  return docline.Text(regex.comment_leader.sub('', line))


def ParseBlockDirective(name, rest):
  if name in docline.BLOCK_DIRECTIVES:
    try:
      return docline.BLOCK_DIRECTIVES[name](rest)
    except ValueError:
      raise error.InvalidBlockArgs(rest)
  raise error.UnrecognizedBlockDirective(name)


def ParseBlocks(lines, filename):
  blocks = []
  selection = []
  lineno = 0
  try:
    for lineno, line in EnumerateParsedLines(lines):
      for block in line.Affect(blocks, selection):
        yield block.Close()
    for block in codeline.EndOfFile().Affect(blocks, selection):
      yield block.Close()
  except error.ParseError as e:
    e.lineno = lineno + 1
    e.filename = filename
    raise
