import inspect

from parm.extensions.extension_registry import ExtensionRegistry
from parm.extensions.execution_context import ExecutionContext
from parm.extensions.injection_context import InjectionContext


class ExtensionBase:
    def __init__(self, extension_registry: ExtensionRegistry):
        self.extension_registry = extension_registry

    def load_extension(self, ext_type):
        self.extension_registry.load_extension(ext_type)


def injected_func(fn):
    if isinstance(fn, str):
        def decorator(func):
            func.injected_name = fn
            func.injected = True
            func.magic_getter = True
            return func
        return decorator

    fn.injected = True
    return fn


def magic_getter(fn):
    if isinstance(fn, str):
        def decorator(func):
            func.getter_name = fn
            func.injected = True
            func.magic_getter = True
            return func
        return decorator

    assert callable(fn)
    fn.injected = True
    fn.magic_getter = True
    return fn


def magic_setter(fn):
    if isinstance(fn, str):
        def decorator(func):
            func.setter_name = fn
            func.injected = True
            func.magic_setter = True
            return func
        return decorator

    fn.injected = True
    fn.magic_setter = True
    return fn


class ExecutionExtensionBase(ExtensionBase):
    def __init__(
            self,
            extension_registry: ExtensionRegistry,
            execution_context: ExecutionContext,
            injection_context: InjectionContext):

        super().__init__(extension_registry)
        self.execution_context = execution_context
        self.injection_context = injection_context

        self.load_injections()

    def get_methods(self):
        return inspect.getmembers(self, predicate=inspect.ismethod)

    def load_injections(self):
        for name, method in self.get_methods():
            if getattr(method, 'injected', False):
                if getattr(method, 'magic_getter', False):
                    name = getattr(method, 'getter_name', name)
                    self.injection_context.inject_magic_getter(name, method)
                elif getattr(method, 'magic_setter', False):
                    name = getattr(method, 'setter_name', name)
                    self.injection_context.inject_magic_setter(name, method)
                else:
                    name = getattr(method, 'injected_name', name)
                    self.injection_context.inject_global(name, method)

    @property
    def cursor(self):
        return self.execution_context.cursor

    @cursor.setter
    def cursor(self, value):
        self.execution_context.cursor = value

    @property
    def match_result(self):
        return self.execution_context.match_result

    @property
    def program(self):
        return self.execution_context.program

    def create_pattern(self, pattern):
        if isinstance(pattern, str):
            pattern = self.program.create_pattern(pattern)
        return pattern
