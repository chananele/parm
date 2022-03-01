from parm.api.env import Env
from parm.api.program import Program


class IDAProgram(Program):
    pass


class IDAMods:
    def __init__(self, idc, idautils):
        self.idc = idc
        self.idautils = idautils


def idapython_create_env():
    import idc
    import idautils
    program = IDAProgram()
    mods = IDAMods(idc, idautils)
    return IDAEnv(program, mods)


class IDAEnv(Env):
    def __init__(self, program, mods):
        super().__init__(program)
        self.mods = mods

    def get_funcs(self):
        raise NotImplementedError()
