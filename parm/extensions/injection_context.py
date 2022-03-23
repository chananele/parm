class InjectionContext:
    def inject_local(self, name, value):
        raise NotImplementedError()

    def inject_global(self, name, value):
        raise NotImplementedError()

    def inject_magic_getter(self, name, callback):
        raise NotImplementedError()

    def inject_magic_setter(self, name, callback):
        raise NotImplementedError()
