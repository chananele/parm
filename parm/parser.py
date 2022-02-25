from lark import Lark


def load_parser():
    parser = Lark.open('arm.lark', rel_to=__file__, parser='lalr')
    t = parser.parse('0x1000: ldm r0, {r0, r2-r5}')
    print(t)


def main():
    load_parser()


if __name__ == '__main__':
    import sys
    sys.exit(main())
