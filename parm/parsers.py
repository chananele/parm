from lark import Lark

from parm.postlex import Spacer, PatternSpacer


class ArmSpacer(Spacer):
    ws_type = '_WS'
    injected_type = '_POST_OPCODE'

    def is_opcode_type(self, token_type):
        return token_type.startswith('OPCODE')

    def is_operand_type(self, token_type):
        return not self.is_opcode_type(token_type)


class ArmPatSpacer(PatternSpacer):
    ws_type = '_WS'
    injected_type = '_POST_OPCODE'
    label_type = 'CAPTURE'

    def is_opcode_type(self, token_type):
        return token_type.startswith('OPCODE')

    def is_operand_type(self, token_type):
        if not self.is_opcode_type(token_type):
            return True
        if 'WILDCARD' in token_type:
            return True
        return False


def create_parser(path, rel_to, start, postlex):
    return Lark.open(path, rel_to=rel_to, parser='lalr', postlex=postlex, start=start)


def create_arm_parser():
    spacer = ArmSpacer()
    return create_parser('lark_files/arm.lark', rel_to=__file__, start='line', postlex=spacer)


def create_arm_pattern_parser():
    spacer = ArmPatSpacer(debug=True)
    return create_parser('lark_files/arm_pat.lark', rel_to=__file__, start='block_pat', postlex=spacer)
