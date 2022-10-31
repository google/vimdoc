Vimdoc - Helpfile generation for vim plugins
============================================

Vimdoc generates vim helpfiles from documentation in vimscript files. You
annotate vimscript like this:

    ""
    " This is my function. It does different things to the {required} argument,
    " depending upon the [optional] argument.
    function! myplugin#MyFunction(required, ...) abort
      ...
    endfunction

and you get helpfiles that look like this:

    ===========================================================================
    FUNCTIONS                                              *myplugin-functions*

    myplugin#MyFunction({required}, [optional])         *myplugin#MyFunction()*
      This is my function. It does different things to the {required} argument,
      depending upon the [optional] argument.

This allows you to keep all of your documentation in one place (the code!) and
generate nicely formatted help files without manually aligning text and adding
tags and so on.

To see an example of vimdoc in use, see
[maktaba](https://github.com/google/maktaba), specifically the
[helloworld](https://github.com/google/maktaba/tree/HEAD/examples/helloworld)
example plugin therein, which shows some of the basics.

**Vimdoc is unstable**. It's a collection of regexes and hacks masquerading as
a complete vim documentation tool. But it works, and it's useful, and it will
continue to be useful while it gets cleaned up.

Installation
------------

Use setup.py to install vimdoc in the usual way. On most systems, this is:

    python setup.py config
    python setup.py build
    sudo python setup.py install

Execution
---------

Run vimdoc on a directory containing a plugin. It will generate a help file in
the 'doc' directory of that plugin. For example:

    vimdoc plugins/myplugin

will generate the helpfile

    plugins/myplugin/doc/myplugin.txt

Usage
-----

Vimdoc operates on comment blocks, which are a continuous group of lines
starting with the "" header:

    ""
    " Documentation for function
    function! ...

Vimdoc automatically recognizes the type of these blocks. It can detect the
following:

- function definitions
- command definitions
- global settings
- maktaba flags
- plugin descriptions (at the top of plugin files)

The names of functions/commands/settings are automatically detected from the
line below the comment block. The arguments for functions/commands are
automatically deduced from the body of the text and (in the case of functions)
from the name of the arguments in the function definition, as follows:

- If the names of all mentioned required arguments in the comment block match
  the names of the arguments in the function definition, then the required
  arguments are ordered according to their placement in the function definition.
- Otherwise, the names used in the comment block are used instead of the names
  used in the function definition, in the order of mention in the comment block.
- Optional arguments (which cannot be named in a function definition, as their
  existence is indicated only by an ellipsis) are used as named in the comment
  block, in the order of mention.

These defaults are usually correct, but can be overridden.

Vimdoc has a number of builtin directives, which are marked by @ signs.

It also detects your plugin's addon-info.json file if present (see the
[documentation](http://vim-wiki.mawercer.de/wiki/topic/addon-info.json.html) and
relevant [VAM help](https://github.com/MarcWeber/vim-addon-manager/blob/HEAD/doc/vim-addon-manager-additional-documentation.txt)).

### Block Directives

Block directives take up an entire line in the comment block. They look like
this:

    ""
    " @usage req1 req2 \[opt1] \[opt2]
    " description...
    function! MyFunction(badName1, badName2, ...)

Available block directives include:

- `@stylized name` allows you to define the stylized version of a plugin name
  (for example, myplugin could be stylized as "My Plugin").
- `@library` marks your plugin as a library plugin. This makes functions public
  by default.
- `@public` marks a function public. In most plugins, functions are private by
  default, though this default may be overridden on a per-plugin basis.
- `@private` marks a function private.
- `@section name[, id]` allows you to write a new section for the helpfile. The
  id will be a lowercased version of name if omitted.
- `@parentsection id` defines the current section as a child of the given
  section. Must be contained within a `@section` block.
- `@subsection name` defines a subsection (heading) within a section block.
- `@backmatter id` declares a block to be rendered at the end of the given
  section.
- `@order ...` allows you to define the order of the sections. Sections with a
  `@parentsection` may not be included here.
- `@dict name` (above blank lines) allows you to define a new dictionary.
- `@dict dict.fn` (above a function) allows you to add a function to
  a dictionary.
- `@usage ...` allows you to rename and reorder the arguments of a function or
  command.
- `@all` denotes that the remainder of the block will be included in all usages
  (in the case of multiple overloaded usages).
- `@function ...` allows you to alter the function tag directly, for when @usage
  does not offer enough control.
- `@command ...` allows you to alter the command tag directly, for when @usage
  does not offer enough control.
- `@setting name` declares a setting (global or per-buffer configuration
  variable).
- `@default arg=value` describes the default value of an optional arg.
- `@throws exception` describes the type of exceptions that a function or
  command may throw.
- `@deprecated reason` marks a command or function as deprecated and excludes it
  from the docs.

The global directives (@stylized, @order, and @library) are all detected from
inside a @section block (usually the Introduction section).

### Inline Directives

Inline directives occur in the body of comment blocks. Most take one argument
enclosed in parenthesis.

- `@function(name)` generates a link to a function defined in the plugin.
- `@command(name)` generates a link to a command defined in the plugin.
- `@flag(name)` generates a link to a flag defined in the plugin.
- `@setting(name)` generates a link to a setting defined in the plugin.
- `@section(id)` generates a link to a section defined in the plugin.
- `@dict(name)` generates a link to a dictionary defined in the plugin.
- `@plugin(attr)` Outputs some plugin data, such as the name or author. `attr`
  must be one of `stylized`, `name`, or `author`. If the attr (and parenthesis)
  are left off, `stylized` is used.

### Other Metadata

Some metadata for your plugin is not configured via vimdoc directives, but comes
from other sources.

By default, the `name` for the plugin is the name of its top-level directory. If
an
[addon-info.json](http://vim-wiki.mawercer.de/wiki/topic/addon-info.json.html)
file is present and contains an explicit "name" field, vimdoc will use that
plugin name instead. This is important if the plugin lives in a directory with a
"vim" prefix or suffix, such as "vim-dispatch". This plugin name will appear in
the helpfile header and determine the name of the helpfile itself.

Vimdoc will also take the `author` and `description` values from the "author"
and "description" fields in addon-info.json.


Syntax
------

Vimdoc syntax is reminiscent of helpfile syntax.

- Use quotes to reference settings, such as 'filetype'.
- Use brackets to reference [optional] function arguments.
- Use braces to reference {required} function arguments.
- Use |pipes| to link to tags in other helpfiles.

Helpfile Structure
------------------

The generated helpfile for a plugin has the following structure:

```
Header
Table of Contents
1. Introduction
2. Configuration
3. Commands
5. Settings
6. Dictionaries
7. Functions
8. Mappings
9. About
```

All of these (except Header and Table of Contents) are optional and predicated
upon the comment blocks existing in the right places in the file. You may
eliminate sections by omitting the comment blocks. You may add custom sections
with the @section directive.

#### Header
The header is a simple line or two following the vim helpfile style guide. It
looks something like:

    *myplugin*     My Plugin’s Tagline
    author                                                *Stylized-Name*

#### Table of Contents
Of the form

    =====================================================================
    CONTENTS                                          *myplugin-contents*
      1. Introduction                                    |myplugin-intro|
      2. Configuration                                  |myplugin-config|
      ...

And so on for each section.

#### Introduction

The introductory comment block is used to populate this section.

#### Configuration

This section contains descriptions of all the flags and settings that were
annotated by vimdoc comment blocks.

Any global `let` command with a doc comment will automatically be detected as a
setting:

    ""
    " Enable a thing.
    let g:myplugin_enable_thing = 1

You can use the `@setting` block directive to declare settings vimdoc doesn't
recognize:

    ""
    " @setting g:myplugin_secret_number
    " A secret number.
    echo 'The number is' get(g:, 'myplugin_secret_number', b:changedtick)

    ""
    " @setting b:myplugin_enable_thing
    " Enable a thing in the current buffer.

Maktaba flags with doc comments are also automatically recognized:

    ""
    " Supported things.
    call s:plugin.Flag('things', ['a', 'b'])

#### Commands

Contains a list of commands available to the user. Vimdoc understands -bang,
-nargs, -range, -count, -register, and -buffer. (It ignores -bar.) It will
parse out the arguments in the order that they are mentioned in the comment
block above the command and will generate a usage line for the command. For
example, the following comment block:

    ""
    " Spawns two new zerglings from the given {hatchery}
    " Attacks all units in the selected [range] upon spawning.
    " [larva], if given, will be used to spawn the zerglings.
    " Otherwise a larva will be selected at random.
    " [!] forces the zerglings to spawn even if you don’t have enough
    " overlords. Caution: this may make your swarm uncontrollable.
    command -range -bang -nargs=+ -bar SpawnZerglings
        \ call zerg#spawn(ZERGLINGS, '<bang>' == '!', <f-args>)

will generate the following usage line:

    :[range]SpawnZerglings[!] {hatchery} [larva]

You can override the usage line with the @usage command, which takes a list of
arguments. Any arguments that look like vim variable names (\I\i+) will be
assumed to be parameters, and their required-ness will be inferred from the
docs. You can force required-ness by providing arguments that look like vim
variables wrapped in curly (required) or square (optional) brackets. Empty
curly brackets stand in for the remainder of the inferred required variables.
Empty square brackets stand in for the remainder of the inferred optional
variables. For example:

    ""
    " @usage {} [first] []
    " Start with {base}, add [second] to [first] and divide by [third].
    command SomeCommand ...

generates:

    :SomeCommand {base} [first] [second] [third]

For more advanced usage, you may use the @command directive. This is useful
either when your command takes a non-standard argument list (like :substitute)
or when your command is not recognized by vimdoc (when you :execute 'command'
s:name).

The @command directive takes one argument, which is the entire usage line. {}
expands to all of the inferred required parameters, [] to all of the inferred
optional parameters, and <> to the complete inferred command name with built-in
flags included. For example:

    ""
    " @command <>/{pattern}/{string}/[flags] [count]
    command -range -bang -nargs=1 Substitute ...

generates the usage line:

    :[range]Substitute[!]/{pattern}/{string}/[flags] [count]

An argument which may be given multiple times should be suffixed with an
ellipsis. For example, {arg...} documents an argument that may appear once or
more and [arg...] denotes an argument that may appear zero or more times.


Sometimes you want a command to have more than one usage. For that you may use
more than one usage directive. Example:

    ""
    " @usage {list} {index} {item}
    " Add {item} to {list} at {index}.
    " @usage {dict} {key} {value}
    " Set {dict} {key} to {value}.
    " @all
    " WARNING: Will launch the nuclear missiles.

This will generate two docs for the command: one for list, one for dicts. An
@all directive denotes that the remainder of the block will be included in all
usages. In the above example, the warning will be included in both the list and
the dict version of the command docs.

#### Dictionaries

Vimscript kinda-sorta supports object oriented programming via dictionaries
with functions attached. (See :help Dictionary-function.) Vimdoc helps you
group these dictionaries and their methods in one place in the documentation.

You may describe a dictionary object type using the @dict annotation in
a comment block that is above a blank line. Then you may annotate the
dictionary functions with the @dict directive to have them grouped with the
dictionary description. (Such functions will not be listed in the functions
section.)

#### Functions

Function documentation is very similar to command documentation.

The order of required parameters is inferred by looking at the function
declaration.

The order of optional parameters is inferred by the order they are mentioned in
the comment block. Use the @usage command as described in the Command section
to correct the order of optional arguments.

Functions may have multiple usages just like commands. Functions are not
exposed in the help docs by default. Use @public to make them public by
default.

@function can be used to tell vimdoc about a non-obvious function (such as one
created by :execute). (), {}, and [] expand as in @command.
