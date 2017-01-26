# -*- coding: utf-8 -*-
"""When you gaze into the abyss, the abyss gazes also into you.

>>> comment_leader.match('  echo "string"')
>>> comment_leader.match('  " Woot') is not None
True
>>> comment_leader.match('"') is not None
True
>>> comment_leader.sub('', '" foo')
'foo'
>>> comment_leader.sub('', '"bar')
'bar'

>>> line_continuation.match('  foo')
>>> line_continuation.match(' \\  foo') is not None
True

>>> blank_comment_line.match('')
>>> blank_comment_line.match('" foo')
>>> blank_comment_line.match('"') is not None
True
>>> blank_comment_line.match('      "         ') is not None
True

>>> blank_code_line.match('foo')
>>> blank_code_line.match('"')
>>> blank_code_line.match('    ') is not None
True
>>> blank_code_line.match('') is not None
True

>>> block_directive.match('  foo')
>>> block_directive.match('  " foo')
>>> block_directive.match('  " @foo').groups()
('foo', '')
>>> block_directive.match('  " @foo bar baz').groups()
('foo', 'bar baz')

>>> section_args.match('')
>>> section_args.match('Introduction').groups()
('Introduction', None)
>>> section_args.match('The Beginning, beg').groups()
('The Beginning', 'beg')

>>> parent_section_args.match('123')
>>> parent_section_args.match('foo').groups()
('foo',)

>>> backmatter_args.match('123')
>>> backmatter_args.match('foo').groups()
('foo',)

>>> dict_args.match('MyDict attr')
>>> dict_args.match('MyDict').groups()
('MyDict', None)
>>> dict_args.match('MyDict.attr').groups()
('MyDict', 'attr')

>>> usage_args.match('foo - bar - baz')
>>> usage_args.match('{foo} bar [][baz]') is not None
True
>>> usage_args.match('{foo...} bar... [][baz...]') is not None
True
>>> usage_arg.findall('{foo} bar [][baz]')
['{foo}', 'bar', '[]', '[baz]']
>>> usage_arg.match('{one..} two.. [three..]')
>>> usage_arg.findall('{one...} two... [three...]')
['{one...}', 'two...', '[three...]']

>>> no_args.match('foo')
>>> no_args.match('') is not None
True

>>> any_args.match('foo') is not None
True
>>> any_args.match('') is not None
True

>>> one_arg.match('foo') is not None
True
>>> one_arg.match('') is None
True

>>> maybe_word.match('Hello There')
>>> maybe_word.match('HelloThere') is not None
True
>>> maybe_word.match('') is not None
True

>>> throw_args.match('-@!813')
>>> throw_args.match('MyError').groups()
('MyError', None)
>>> throw_args.match('MyError on occasion').groups()
('MyError', 'on occasion')

>>> default_args.match('foo!bar')
>>> default_args.match('{foo}=bar')
>>> default_args.match('[foo]=bar').groups()
('[foo]', 'bar')
>>> default_args.match('foo=bar').groups()
('foo', 'bar')
>>> default_args.match('someVar = Some weird ==symbols==').groups()
('someVar', 'Some weird ==symbols==')

>>> order_args.match('some* weird! id"s')
>>> order_args.match('foo bar baz') is not None
True
>>> order_args.match('foo bar baz +').groups()
('foo bar baz +',)
>>> order_arg.findall('foo bar baz -')
['foo', 'bar', 'baz', '-']

>>> stylizing_args.match('Your Plugin')
>>> stylizing_args.match('MyPlugin').groups()
('MyPlugin',)
>>> stylizing_args.match('っoの').groups()
('っoの',)

>>> function_line.match('foo bar')
>>> function_line.match('fu MyFunction()').groups()
(None, 'MyFunction', '')
>>> function_line.match('funct namespace#MyFunction(foo, bar)').groups()
('namespace#', 'MyFunction', 'foo, bar')
>>> function_line.match('fu!a#b#c#D(...) abort dict range').groups()
('a#b#c#', 'D', '...')

>>> command_line.match('com -nargs=+ -bang MyCommand call #this').groups()
('-nargs=+ -bang ', 'MyCommand')

>>> setting_line.match('let s:myglobal_var = 1')
>>> setting_line.match('let g:myglobal_var = 1').groups()
('myglobal_var',)
>>> setting_line.match('let g:mysettings.var = 0').groups()
('mysettings.var',)

>>> flag_line.match("call s:plugin.Flag('myflag')")
>>> flag_line.match("call s:plugin.Flag('myflag', 0)").groups()
('myflag', None, '0')
>>> flag_line.match('cal g:my["flags"].Flag("myflag", 1)').groups()
(None, 'myflag', '1')
>>> flag_line.match("call s:plugin.Flag('Some weird '' flag', 'X')").groups()
("Some weird '' flag", None, "'X'")
>>> flag_line.match(
...     r'call s:plugin.Flag("Another \\" weird flag", [])').groups()
(None, 'Another \\\\" weird flag', '[]')
>>> flag_line.match("call s:plugin.Flag('myflag', 1)").groups()
('myflag', None, '1')
>>> flag_line.match('call s:plugin.Flag("myflag",   '
...     "get(g:, 'foo', [])  )").groups()
(None, 'myflag', "get(g:, 'foo', [])")

>>> numbers_args.match('1 two 3')
>>> numbers_args.match('1 2 3').groups()
('1 2 3',)
>>> number_arg.findall('1 2 3')
['1', '2', '3']

>>> vim_error.match('EVERYTHING')
>>> vim_error.match('E101') is not None
True

>>> inline_directive.match('@function(bar)').groups()
('function', 'bar')
>>> inline_directive.sub(
...     lambda match: '[{}]'.format(match.group(2)),
...     'foo @function(bar) baz @link(quux) @this')
'foo [bar] baz [quux] [None]'

>>> function_arg.findall('foo, bar, baz, ...')
['foo', 'bar', 'baz', '...']

>>> bad_separator.search('foo, bar, baz')
>>> bad_separator.search('foo bar baz')
>>> bad_separator.search('foo, , bar, baz') is not None
True
>>> bad_separator.search('foo  bar  baz') is not None
True
>>> bad_separator.sub('', 'foo  bar, , baz')
'foo bar, baz'

>>> vimdoc_leader.match('"" Foo') is not None
True
>>> vimdoc_leader.match('""') is not None
True
>>> vimdoc_leader.match('" " ')
>>> empty_vimdoc_leader.match('  ""') is not None
True
>>> empty_vimdoc_leader.match('""  ')

"""
import re


def _DelimitedRegex(pattern):
  return re.compile(r"""
    # Shouldn't follow any non-whitespace character.
    (?<!\S)
    # pattern
    (?:{})
    # Shouldn't be directly followed by alphanumeric (but "," and "." are okay).
    (?!\w)
  """.format(pattern), re.VERBOSE)


# Regular expression soup!
vimdoc_leader = re.compile(r'^\s*"" ?')
empty_vimdoc_leader = re.compile(r'^\s*""$')
comment_leader = re.compile(r'^\s*" ?')
line_continuation = re.compile(r'^\s*\\')
blank_comment_line = re.compile(r'^\s*"\s*$')
blank_code_line = re.compile(r'^\s*$')
block_directive = re.compile(r'^\s*"\s*@([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+|$)(.*)')
section_args = re.compile(r"""
  ^
  # MATCH GROUP 1: The Name
  (
    # Non-commas or escaped commas or escaped escapes.
    # Must not end with a space.
    (?:[^\\,]|\\.)+\S
  )
  # Optional identifier
  (?:
    # Separated by comma and whitespace.
    ,\s*
    # MATCHGROUP 2: The identifier
    ([a-zA-Z_-][a-zA-Z0-9_-]*)
  )?
  $
""", re.VERBOSE)
parent_section_args = re.compile(r'([a-zA-Z_-][a-zA-Z0-9_-]*)')
backmatter_args = re.compile(r'([a-zA-Z_-][a-zA-Z0-9_-]*)')
dict_args = re.compile(r"""
  ^([a-zA-Z_][a-zA-Z0-9]*)(?:\.([a-zA-Z_][a-zA-Z0-9_]*))?$
""", re.VERBOSE)
default_args = re.compile(r"""
  ^( # MATCH GROUP 1: The variable name.
    (?: # Any of:
      # Square brackets with an identifier within.
      \[[a-zA-Z_][a-zA-Z0-9_]*\]
    |
       # An identifier
      [a-zA-Z_][a-zA-Z0-9_]*
    )
  ) # An equals sign, optional spaces.
  \s*=\s*
  # MATCH GROUP 2: The value.
  (.*)$
""", re.VERBOSE)
numbers_args = re.compile(r'^((?:\s|\d)*)$')
number_arg = re.compile(r'\d+')
usage_args = re.compile(r"""
  ^((?:
    # Optional separating whitespace.
    \s*
    (?:
      # Curly braces with an optional identifier within.
      {(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)?}
    |
      # Square brackets with an optional identifier within.
      \[(?:[a-zA-Z_.][a-zA-Z0-9_.]*(?:\.\.\.)?)?\]
    |
      # An identifier
      [a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?
    |
      # A joint argument hole
      {\]
    )
    # Many times.
  )*)$
""", re.VERBOSE)
usage_arg = re.compile(r"""
    # Curly braces with an optional identifier within.
    {(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)?}
  |
    # Square brackets with an optional identifier within.
    \[(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)?\]
  |
    # The special required-followed-by-optional hole
    {\]
  |
    # An identifier
    [a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?
""", re.VERBOSE)
order_args = re.compile(r'^((?:\s*[a-zA-Z_][a-zA-Z0-9_-]*)+(?:\s*[+-])?)$')
order_arg = re.compile(r'([a-zA-Z_][a-zA-Z0-9_-]*|[+-])')
no_args = re.compile(r'^$')
any_args = re.compile(r'^(.*)$')
one_arg = re.compile(r'^(.+)$')
maybe_word = re.compile(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)?\s*$')
throw_args = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+(.*))?$')
vim_error = re.compile(r'^E\d+$')
stylizing_args = re.compile(r'^(\S+)$')
function_line = re.compile(r"""
  # Leading whitespace.
  ^\s*
  # fu[nction]
  fu(?:n|nc|nct|ncti|nctio|nction)?
  # Separation (with an optional bang)
  (?:\s*!\s*|\s+)
  # GROUP 1: Autocmd namespace.
  ((?:[a-zA-Z_][a-zA-Z0-9_]*\#)+)?
  # GROUP 2: Function name.
  ([a-zA-Z_][a-zA-Z0-9_]*)
  # Open parens
  \s*\(
  # GROUP 3: Parameters
  # This is more permissive than it has to be. Vimdoc is not a parser.
  ([^\)]*)
  # Close parens
  \)
""", re.VERBOSE)
command_line = re.compile(r"""
  # Leading whitespace.
  ^\s*
  # com[mand]
  com(?:m|ma|man|mand)?
  # Optional bang.
  (?:\s*!\s*|\s+)
  # GROUP 1: Command arguments.
  ((?:-\S+\s*)*)
  # GROUP 2: Command name.
  ([a-zA-Z_][a-zA-Z0-9_]*)
""", re.VERBOSE)
setting_line = re.compile(r"""
  # Definition start.
  ^\s*let\s+g:
  # GROUP 1: Setting name.
  # May include [] (indexing), {} (interpolation), and . (dict of settings).
  ([a-zA-Z_][a-zA-Z0-9_{}\[\].]*)
""", re.VERBOSE)
setting_scope = re.compile(r'[a-z]:')
flag_line = re.compile(r"""
  # Definition start.
  ^\s*call?\s*.*\.Flag\(
  # Shit's about to get real.
  (?:
    # GROUP 1: The flag name in single quotes.
    '(
      # Double single quotes escapes single quotes.
      (?:[^']|'')*
    )'
  | # GROUP 2: The flag name in double quotes.
    "(
      # No escapes or double quotes, or one escaped anything.
      (?:[^\\"]|\\.)*
    )"
  ),\s*
  (?:
    # GROUP 3: Default value.
    ((?:
      # Any non-parenthesis character.
      [^()]
    | # Any non-parenthesis character inside a pair of parentheses. Doesn't
      # handle nesting to arbitrary depth.
      \([^()]+\)
    )+?)
    \s*\)
  )?
""", re.VERBOSE)
inline_directive = re.compile(r'@([a-zA-Z_][a-zA-Z0-9_]*)(?:\(([^\s)]+)\))?')

name_hole = re.compile(r'<>')
arg_hole = re.compile(r'{\]')
required_hole = _DelimitedRegex(r'{}')
optional_hole = _DelimitedRegex(r'\[\]')
required_arg = _DelimitedRegex(r'{([a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)}')
optional_arg = _DelimitedRegex(r'\[([a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)\]')
namehole_escape = re.compile(r'<\|(\|*)>')
requiredhole_escape = re.compile(r'{\|(\|*)}')
optionalhole_escape = re.compile(r'\[\|(\|*)\]')
bad_separator = re.compile(r"""
  (?:
    # Extra comma-spaces
    (?:,\ )+(?=,\ )
  |
    # Multiple spaces
    \ +(?=\ )
  )
""", re.VERBOSE)

function_arg = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*|\.\.\.)')

list_item = re.compile(r'^\s*([*+-]|\d+\.)\s+')
