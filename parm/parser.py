from lark import Lark

from postlex import ArmSpacer


class Spacer(ArmSpacer):
    ws_type = '_WS'
    injected_type = '_POST_OPCODE'

    def is_opcode_types(self, token_type):
        return token_type.startswith('OPCODE')


def load_parser():
    spacer = Spacer()
    parser = Lark.open('arm.lark', rel_to=__file__, parser='lalr', postlex=spacer)
    print(parser.parse('0x1000: ldm r0, {r0, r2-r5}'))
    print(parser.parse('strbeq r2, [r4, lsl#8]'))
    print(parser.parse('LDR R8, [R0, R0, ASR#31]'))
    print(parser.parse('25: blx lr'))
    print(parser.parse('25: beq 0x2000'))


def main():
    load_parser()


if __name__ == '__main__':
    import sys
    sys.exit(main())
