"""The vimdoc parser."""
from vim_plugin_metadata import VimNode, VimParser

from vimdoc import codeline
from vimdoc import docline
from vimdoc import error
from vimdoc import regex
from vimdoc.block import Block


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


def ParseBlocksForNodeDocComment(doc, blocks, selection):
  if doc is None:
    return
  for line in doc.splitlines():
    yield from ParseCommentLine(f'" {line}').Affect(blocks, selection)

def AffectForVimNode(node, blocks, selection):
  if isinstance(node, VimNode.StandaloneDocComment):
    yield from ParseBlocksForNodeDocComment(node.doc, blocks, selection)
    yield from codeline.Blank().Affect(blocks, selection)
    return
  doc = getattr(node, 'doc', None)
  yield from ParseBlocksForNodeDocComment(doc, blocks, selection)
  if isinstance(node, VimNode.Function):
    yield from ParseCodeLine('func{bang} {name}({args}) {modifiers}'.format(
        name=node.name,
        args=', '.join(node.args),
        bang='!' if '!' in node.modifiers else '',
        modifiers=' '.join(mod for mod in node.modifiers if mod != '!')
      )).Affect(blocks, selection)
  elif isinstance(node, VimNode.Command):
    yield from ParseCodeLine("command {modifiers} {name}".format(name=node.name, modifiers=' '.join(node.modifiers))).Affect(blocks, selection)
  elif isinstance(node, VimNode.Variable):
    yield from ParseCodeLine("let {name} = {rhs}".format(
      name=node.name,
      rhs=node.init_value_token,
    )).Affect(blocks, selection)
  elif isinstance(node, VimNode.Flag):
    yield from ParseCodeLine("call s:plugin.Flag('{name}', {default_value_token})".format(name=node.name, default_value_token=node.default_value_token)).Affect(blocks, selection)

def ParsePluginModule(module):
  unclosed_blocks = []
  selection = []
  yield from ParseBlocksForNodeDocComment(module.doc, unclosed_blocks, selection)
  yield from codeline.Blank().Affect(unclosed_blocks, selection)

  for node in module.nodes:
    yield from AffectForVimNode(node, unclosed_blocks, selection)
  yield from codeline.EndOfFile().Affect(unclosed_blocks, selection)

def ParsePluginDir(directory):
  vim_parser = VimParser()
  for module in vim_parser.parse_plugin_dir(directory).content:
    module_blocks = [block.Close() for block in ParsePluginModule(module)]
    yield (module, module_blocks)
