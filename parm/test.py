from parm import parsers, transformers


def load_trees(parser):
    return [
        parser.parse('0x1000: ldm r0, {r0, r2-r5, lr, pc}'),
        parser.parse('ldr r1, [r1]'),
        parser.parse('strbeq r2, [r4, #8]'),
        parser.parse('LDR R8, [R0, #4]!'),
        parser.parse('25: blx lr'),
        parser.parse('25: beq 0x2000'),
        parser.parse('adc r0, r1'),
        parser.parse('SUB r0, r1, r2, lsl#6'),
        parser.parse('mov r0, r3, lsl#30'),
        parser.parse('mov r0, #5'),
        parser.parse('ldrne r0, [r4, r1, asr#4]!'),
    ]


def main():
    parser = parsers.create_arm_parser()
    trees = load_trees(parser)
    transformer = transformers.ArmTransformer()
    for tree in trees:
        result = transformer.transform(tree)
        print(result)


if __name__ == '__main__':
    import sys
    sys.exit(main())
