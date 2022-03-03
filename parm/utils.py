def indent(string: str, spaces=4):
    indentation = ' ' * spaces
    lines = string.splitlines(True)
    return ''.join([indentation + line for line in lines])
