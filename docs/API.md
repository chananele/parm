# Examples

Below are a few examples meant to show how one might use parm to analyze a
binary.
The APIs are still **very much** a work in progress, and subject to change.

#### Basic Pattern Matching
The following example shows how to match a pattern at a given address.

```python
from parm.api.match_result import MatchResult
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()
mr = MatchResult()

# Match a pattern at a specified address
cursor = prg.create_cursor(0x1000)
cursor.match("""
    ldr @:reg, [r1]
    mov r0, #5
""", mr)
print(f'Reg: {mr["reg"]}')
```

#### Program Wide Search
Sometimes, you want to run a pattern match on an entire program.
In the following example, a very simple pattern is used to try and
find all function prologues in a program.

```python
from parm.api.match_result import MatchResult
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()
mr = MatchResult()

prg.find_all("""
func_start:
    push {*, lr}
""", mr, scope_name='prologues')
results = mr.subs['prologues']
print('Funcs:', [m['func_start'] for m in results])
```

#### Code Patterns
The real power of `parm` comes from its extension model, called "code patterns".
Code patterns are just pieces of code (usually one-liners) interspersed in 
regular patterns. Code patterns are called using the `%code_pattern` or `!code_pattern` syntax.

As mentioned, although it may not look it, the code patterns are in fact 
pure python code.
Code patterns are called from the current matching context.
The code pattern may modify the current cursor, which will affect the
rest fo the pattern.
If the current cursor is not modified, the next pattern will be matched
against the same cursor.

Aside from that, code patterns may do anything - they are just regular 
python code!
For example, a code pattern may also modify the current match context,
by adding matches.

```python
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()

match = prg.find_symbol('func_impl').match("""
    !match_single(xrefs_to, "callers")
    {
        !fn_start
        func:
    }
""")
print('func:', match['func'])
```
In the above example, a two code patterns where used, each one using a
special object, called a *contextual injection*.

*Contextual injections*, or just *injections*, are special objects that are
injected by `parm` into the execution environment in which code patterns run.
There are many *injections* that come builtin with `parm`, some generic and
some specific to certain architectures or program types (e.g. capstone vs. IDA).

The *injections* used in the preceding example are:
1. `xrefs_to` - An iterator of cursors from which there are xrefs to the current
   cursor. This *injection* is provided by the `IDAProgram`, and is implemented
   using IDAs functionality of the same name.
2. `fn_start` - A cursor that points to the start of the function in which the
   cursor currently resides. This *injection* is also provided by the 
   `IDAProgram`, using IDA functionality.


There is another type of code pattern, called a *code multi-pattern*.  
*Code multi-patterns* are called using the `$code_pattern` syntax.

Sometimes a pattern cannot be described using the simple linear flow
given in the preceding examples.

For example, sometimes, you may want to assert that all xrefs to a
function match a given pattern.
With the previously shown syntax, this is not possible.
Consecutive lines only filter out potential matches, until the end
of the pattern is reached or no more cursors are left.

This is where *code multi-patterns* come into play.

The difference between regular code patterns and code multi-patterns 
is that regular code patterns are called for each cursor at the current 
line, whereas multi-patterns are called once with all the cursors at
the current line.

An example usage of a code multi-pattern is given below:

```python
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()

match = prg.find_symbol('func_impl').match("""
    !expect(xrefs_to) == 2
    !match_all(xrefs_to)
    {
        !fn_start
        func:
    }
""")
```

The above example is almost identical to the one above it, except for
the line `$expect(len(cursors) == 2)`.
The previous example would match, so long as all xrefs to `func_impl` 
belonged to the same function (otherwise there would be a collision 
in the `func` capture variable).
This example, additionally, requires that there be exactly two xrefs 
to `func_impl`.

This example also introduced a new *injection* - the `expect()` function.
This *injection* checks a condition, and fails the match if the condition
evaluates to false.

This also allows for other interesting features, specifically with relation
to nested patterns, which we will discuss below.

#### Nested Patterns

A nested pattern is defined with the following syntax.
```
% pattern <name> {
    pattern...
}
```

Nested patterns are commonly used in conjunction with 
*code multi-patterns*, such as:
* `match_all(pat)` - Given a pattern (possibly nested), attempts to match
  all cursors at the current line with the given pattern.  
  If even a single cursor does not match, the entire match fails.
* `match_single(pat)` - Given a pattern (possibly nested), attempts to match
  all cursors at the current line with the given pattern.  
  One, and only one cursor may match the pattern, otherwise that entire 
  match fails.
* `match_any(pat)` - Given a pattern (possibly nested), attempts to match
  all cursors at the current line with the given pattern.  
  Any number of matches may succeed, including zero.
* `match_some(pat)` - Like `match_any`, but the number of matches must be
  greater than zero.

An example using a nested match along with `$match_all`:

```python
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()

match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !goto('reset_logic')
    
    !filter
    {
        BL @:reset_logic
    }
    
    !match_all(xrefs_to, 'reg_saves')
    {
        MOV @:reg, R0
    }
""")
for s in match.subs['reg_saves']:
    print(s['reg'])
```
The above example will only match if all calls to `reset_logic` 
(the function called at the reset vector) are followed by storing
the result (the `R0` register) in a register.
If a single call to the reset vector does not meat this requirement,
the entire match will fail.

You may have also noticed a new *injection* - The `jump_target` injection.
This *injection* moves the cursor to the target of the branch to which 
the cursor currently points.

Below, another example is given, using a nested match along
with `$match_single`:

```python
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()

match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !jump_target
    
    !match_single(xrefs_to)
    {
        BL  @:reset_logic  // Filter out any jumps (as opposed to calls) 
        MOV R12, R0
        ADR R0, @:storage
        STR R12, R0
    }
""")
s = match.sub[0]
print(s['storage'])
assert s['reset_logic'] == match['reset_logic']
```

The above example also shows a couple of interesting features:
* The name of the nested match is optional!  
  Aside from accessing nested match results via names, indices may
  also be used, although this is discouraged for large patterns.
* Match results from parent patterns may be accessed from nested 
  results.

#### Capture Scoping
So far, we have just used capture expressions 
(such as `MOV @:capture, R0` or `address: LDR R1, [R1]`).
They have just been created implicitly.  
Once they are created, they must remain the same while they are
in scope. If there is a collision, it is considered a mismatch.

The scoping of variables allows us to capture multiple values 
as shown in the preceding example with "reg_saves".  
But what if we didn't want there to be multiple `reg` captures?  
What if we wanted there to be a single `reg` that all nested matches
have to match?

It is for this purpose the `% var` syntax is introduced.  
`% var` can be used to declare a variable in a single scope, 
forcing all captures in nested patterns to match the single 
variable.

This is demonstrated in the following example:

```python
from parm.programs.ida import idapython_create_program

prg = idapython_create_program()

match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !jump_target
    
    !xrefs_to
    BL  @:reset_logic  // Filter out any jumps (as opposed to calls) 
    
    %pattern p {
        // If not all BLs to `reset_logic_impl` immediately store
        // R0 in the same register after returning, the entire 
        // pattern match will fail.
        MOV @:result_reg, R0
        LDR @:other_reg, R5
    }
    
    $match_some(p, cursors, name='x', unique=('result_reg', ))
""")
print(match['result_reg'])
s = match.subs['x']
for m in s:
    print(m['other_reg'])
```
