from parm.envs.base_env import BaseEnv


class IDAMods:
    def __init__(self, idc, idautils):
        self.idc = idc
        self.idautils = idautils


def idapython_create_env():
    import idc
    import idautils
    mods = IDAMods(idc, idautils)
    return IDAEnv(mods)


class IDAEnv(BaseEnv):
    def __init__(self, mods):
        self.mods = mods
