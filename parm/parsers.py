from lark import Lark


def create_parser(path, rel_to, start, postlex=None, parser='earley', lexer=None, **kwargs):
    if postlex is not None:
        kwargs['postlex'] = postlex
    if parser is not None:
        kwargs['parser'] = parser
    if lexer is not None:
        kwargs['lexer'] = lexer

    return Lark.open(path, rel_to=rel_to, start=start, **kwargs)


def create_arm_parser():
    return create_parser('lark_files/arm.lark', rel_to=__file__, start='line')


def create_arm_pattern_parser():
    return create_parser('lark_files/arm_pat.lark', rel_to=__file__, start='block_pat')
