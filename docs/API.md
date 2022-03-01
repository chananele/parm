# Examples

Below are a few examples meant to show how one might use parm to analyze a
binary.
The APIs are still **very much** a work in progress, and subject to change.

```python
from parm.envs.ida import idapython_create_program
prg = idapython_create_program()
env = prg.env

# Match a pattern at a specified address
cursor = prg.create_cursor(0x1000)
result = cursor.match("""
    ldr @:reg, [r1]
    mov r0, #5
""")
print(f'Reg: {result["reg"]}')

results = prg.find_all("""
func_start:
    push {*, lr}
""")
print('Funcs:', [m['func_start'] for m in results])

# The following code is an example of using extensions - the feature
# that brings real power to parm.
# Extensions are called in a line beginning with a '!'.
# Although it may not look it, the extension line is in fact pure python.
# An extension run from the context of a cursor, and must return either a
# cursor or an iterator of cursors.

# In this example, `xrefs` returns an iterator over all the xrefs to the
# location of the current cursor.
# The `xrefs` extension here is implemented over the same IDA functionality.
# The `func_start` extension returns a cursor pointing to the start of the 
# function in which the cursor currently resides.
# This too is implemented using the provided IDA functionality.

# Although the mentioned extensions are provided by IDA, one may develop 
# their own extensions, allowing for a very flexible plugin interface.
syscalls = prg.find_symbol('generic_syscall_impl').match("""
    !xrefs
    !func_start
caller:
""")
print('Syscalls:', [m['caller'] for m in syscalls])

# Sometimes a pattern can be comprised of multiple blocks
# The following examples show some simpler types of composite patterns,
# and some more complicated

match = prg.create_cursor(0).match("""
    B @:reset_logic
    !jump_target
    LDR R0, [@]
    BL  @:real_logic
    !jump_target
    !xrefs
    
    // Many cursors - match attribute required!
    // A match attribute of "[all]" means all cursors must
    // Match the contained pattern - if one of them does not,
    // the entire match will fail.
    // Providing a name for the match (in this case "reg_saves")
    // is optional but required in order to access captured values.
    % match reg_saves [all] {
        BL  @:real_logic  // Check that all xrefs are BL instructions
        MOV @:reg, R0
    }
    
    // By setting the "[single]" attribute, one and only one xref may
    // match the following pattern.
    % match [single] {
        BL  @:real_logic
        MOV R12, R0
    }
    
    // Setting "[any]" means that at least one xref must match the
    // given pattern, but possibly more.
    // When an attribute is not specified, this is the default.
    % match [any] {
        BL   @
        MOV  R1, R0
    }
    
    // If not matched, no harm done.
    % match [optional] {
        !skip(5)  // Skip 5 instructions
    maybe:
        MOV @, #0
    }
""")
print(match['real_logic'])
rsm = match.sub_matches('reg_saves')
assert isinstance(rsm, list)
for m in rsm:
    print(m['reg'])

# You may have noticed that captured values have scopes - for 
# examples, the "reg" capture was in the "reg_saves" scope, while
# "real_logic" is in the root pattern scope.
# The scope of a capture is actually important - if a variable was
# defined in a "broader" scope, a more nested scope must match it.

# Since "reg_saves" is defined in a `match [all]` scope, multiple
# values may have been captured.
# This is why you must call `sub_matches`, which returns a list.  

# The following example shows how to declare a capture at a higher
# scope in order to force all nested patterns to match a single
# value
match = prg.create_cursor(0).match("""
    B   @:reset_logic
    !jump_target
    BL  @:reset_logic_impl
    !jump_target
    !xrefs
    BL   @  // Filter out any other xref types
    // We are right after the return from the call
    
    % var result_reg
    % match [all] {
        MOV @:result_reg, R0
    }
""")
print(match['result_reg'])
# As you can see, there is a single match for "result_reg", and
# it can be accessed directly from the root match.
```
