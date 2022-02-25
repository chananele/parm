from lark import Lark


def load_parser():
    parser = Lark.open('arm.lark', rel_to=__file__, parser='lalr')
    print(parser.parse('0x1000: ldm r0, {r0, r2-r5}'))
    print(parser.parse('strbeq r2, [r4, lsl#8]'))
    print(parser.parse('LDR R8, [R0, R0, ASR#31]'))


def main():
    load_parser()


if __name__ == '__main__':
    import sys
    sys.exit(main())
