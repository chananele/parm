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
print("Funcs:")
for m in results:
    print(f'\t{m["func_start"]}')
```
