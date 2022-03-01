# Examples

Below are a few examples meant to show how one might use parm to analyze a
binary.
The APIs are still **very much** a work in progress, and subject to change.

```python
from parm.envs.ida import idapython_create_env
env = idapython_create_env()

# Match a pattern at a specified address
cursor = env.create_cursor(0x1000)
result = env.match("""
    ldr @:reg, [r1]
    mov r0, #5
""", cursor=cursor)
print(f'Reg: {result["reg"]}')

results = env.find_all("""
func_start:
    push {*, lr}
""")
print("Funcs:")
for m in results:
    print(f'\t{m["func_start"]}')
```
