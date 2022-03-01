from parm.api.embedded_ns import EmbeddedLocalNS


class Env:
    def __init__(self):
        self._embedded_ns = EmbeddedLocalNS()

    def add_magic(self, name, callback):
        self._embedded_ns.add_magic(name, callback)
