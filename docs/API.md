# Examples

Below are a few examples meant to show how one might use parm to analyze a
binary.
The APIs are still **very much** a work in progress, and subject to change.

```python
from parm.envs.ida import idapython_create_env
env = idapython_create_env()
result = env.match("""
    ldr @:reg, [r1]
""", cursor=env.create_cursor(0x1000))
print(f'Reg: {result["reg"]}')
```
