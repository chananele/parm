# Examples

Below are a few examples meant to show how one might use parm to analyze a
binary.
The APIs are still **very much** a work in progress, and subject to change.

#### Basic Pattern Matching
The following example shows how to match a pattern at a given address.
```python
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()

# Match a pattern at a specified address
cursor = prg.create_cursor(0x1000)
result = cursor.match("""
    ldr @:reg, [r1]
    mov r0, #5
""")
print(f'Reg: {result["reg"]}')
```

#### Program Wide Search
Sometimes, you want to run a pattern match on an entire program.
In the following example, a very simple pattern is used to try and
find all function prologues in a program.
```python
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()

results = prg.find_all("""
func_start:
    push {*, lr}
""")
print('Funcs:', [m['func_start'] for m in results])
```

#### Code Patterns
The real power of `parm` comes from its extension model, called "code patterns".
Code patterns are just pieces of code (usually one-liners) interspersed in 
regular patterns. Code patterns are called using the `!code_pattern` syntax.

As mentioned, although it may not look it, the code patterns are in fact 
pure python code.
Code patterns are called from the current matching context, and must
return either a cursor or an iterator of cursors.
Aside from that, code patterns may do anything - they are just regular 
python code!
For example, a code pattern may also modify the current match context,
by adding matches.
```python
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()

syscalls = prg.find_symbol('generic_syscall_impl').match("""
    !xrefs_to
    !fn_start
caller:
""")
print('Syscalls:', [m['caller'] for m in syscalls])
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

#### Nested Patterns
Sometimes a pattern cannot be described using the simple linear flow
given in the preceding examples.

For example, sometimes, you may want to assert that all xrefs to a
function match a given pattern.
With the previously shown syntax, this is not possible.
Consecutive lines only filter out potential matches, until the end
of the pattern is reached or no more cursors are left.

It is for this purpose that the *match block* syntax is provided.

A *match block* is a pattern that is matched against all current 
cursors. The behavior of a *match block* changes, depending on its type.

The syntax for a *match block* is as follows:
```
% match <name> [<type>] {
    pattern...
}
```

The types of possible *match blocks* are:
* `all` - All cursors **must** match the enclosed pattern.
* `single` - There **must** be one, and only one cursor that 
  matches the enclosed pattern.
* `+` - There **must** be at least one cursor that matches the
  enclosed pattern, but there may be more.
* `*` - There **may** be any number of cursors that match the 
  enclosed pattern, but it is not required to be so.
* `?` - There **may** be one cursor that matches the enclosed
  pattern, but there may not be more.

An example of an `[all]` type nested match:
```python
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()

match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !jump_target
    !xrefs_to
    BL  @:reset_logic  // Filter out any jumps (as opposed to calls) 
    
    % match reg_saves [all] {
        MOV @:reg, R0
    }
""")
for m in match.subs['reg_saves']:
    print(m['reg']) 
```
The above example will only match if all calls to `reset_logic` 
(the function called at the reset vector) are followed by storing
the result (the `R0` register) in a register.
If a single call to the reset vector does not meat this requirement,
the entire match will fail.

The above example also showed how you can access the results of 
a nested pattern match.
If multiple matches are allowed (`[all]`, `[*]`, `[+]`), the 
results must be accessed via the `subs` property. If at most 
one match is permitted (`[single]`, `[?]`), the results must
be accessed via the `sub` property.

You may have also noticed a new *injection* - The `jump_target` injection.
This *injection* moves the cursor to the target of the branch to which 
the cursor currently points.

Another example is given, demonstrating a `[single]` type nested pattern:
```python
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()

match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !jump_target
    !xrefs_to
    BL  @:reset_logic  // Filter out any jumps (as opposed to calls) 
    
    % match [single] {
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
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()

match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !jump_target
    !xrefs_to
    BL  @:reset_logic  // Filter out any jumps (as opposed to calls) 
    
    % var result_reg
    % match [+] {
        // If not all BLs to `reset_logic_impl` immediately store
        // R0 in the same register after returning, the entire 
        // pattern match will fail.
        MOV @:result_reg, R0
        LDR @:other_reg, R5
    }
""")
print(match['result_reg'])
s = match.subs[0]
for m in s:
    print(m['other_reg'])
```
