from lark import Lark


def create_parser(path, rel_to, start, postlex=None, parser='earley', lexer=None):
    if parser == 'earley' and lexer is None:
        lexer = 'dynamic_complete'
    return Lark.open(path, rel_to=rel_to, parser=parser, postlex=postlex, start=start, lexer=lexer)


def create_arm_parser():
    return create_parser('lark_files/arm.lark', rel_to=__file__, start='line')


def create_arm_pattern_parser():
    return create_parser('lark_files/arm_pat.lark', rel_to=__file__, start='block_pat')
