from lark import Lark

from parm.postlex import Spacer


def create_parser(path, rel_to=None, start=None):
    spacer = Spacer()
    return Lark.open(path, rel_to=rel_to, parser='lalr', postlex=spacer, start=start)


def create_arm_parser():
    return create_parser('arm.lark', rel_to=__file__, start='line')
