from parm.api.env import Env
from parm.api.program import Program
from parm.api.asm_cursor import AsmCursor
from parm.api.type_hints import ReversibleIterable

from parm.extensions.extension_base import magic_getter
from parm.extensions.default_extensions import AnalysisExtension


class IDAAnalysisExt(AnalysisExtension):
    @magic_getter('xrefs_to')
    def get_xrefs_to(self, cursor):
        raise NotImplementedError()

    @magic_getter('xrefs_from')
    def get_xrefs_from(self, cursor):
        raise NotImplementedError()


class IDAMods:
    def __init__(self, idc, idautils):
        self.idc = idc
        self.idautils = idautils


class IDAProgram(Program):
    def __init__(self, env, mods):
        super().__init__(env)
        self.mods = mods

    def register_default_extensions(self):
        super(IDAProgram, self).register_default_extensions()
        self.register_extension_type(IDAAnalysisExt)

    def create_cursor(self, address) -> AsmCursor:
        raise NotImplementedError()

    def create_pattern(self, pattern):
        raise NotImplementedError()

    def find_symbol(self, symbol_name) -> AsmCursor:
        raise NotImplementedError()

    @property
    def cursors(self) -> ReversibleIterable[AsmCursor]:
        raise NotImplementedError()


# noinspection PyUnresolvedReferences,PyPackageRequirements
def idapython_create_program() -> IDAProgram:
    import idc
    import idautils
    mods = IDAMods(idc, idautils)
    env = Env.create_default_env()
    return IDAProgram(env, mods)
