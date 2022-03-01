from parm.api.env import Env
from parm.api.func import Func
from parm.api.program import Program


class IDAMods:
    def __init__(self, idc, idautils):
        self.idc = idc
        self.idautils = idautils


class IDAFunc(Func):
    pass


class IDAProgram(Program):
    def __init__(self, env, mods):
        super().__init__(env)
        self.mods = mods

    def get_func(self, cursor):
        raise NotImplementedError()

    def get_xrefs(self, cursor):
        raise NotImplementedError()

    def add_env_magics(self):
        self.env.add_magic('xrefs', self.get_xrefs)
        self.env.add_magic('func', self.get_func)


def idapython_create_program() -> IDAProgram:
    import idc
    import idautils
    mods = IDAMods(idc, idautils)
    env = Env()
    return IDAProgram(env, mods)
