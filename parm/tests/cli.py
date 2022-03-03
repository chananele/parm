from parm import parsers
from parm.transformers import arm, arm_pattern


def load_arm_code_trees(parser):
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


def test_arm_code():
    parser = parsers.create_arm_parser()
    trees = load_arm_code_trees(parser)
    transformer = arm.ArmTransformer()
    for tree in trees:
        result = transformer.transform(tree)
        print(repr(result))


def load_arm_pattern_trees(parser):
    yield parser.parse('blx* r0')
    yield parser.parse('beq @:target')
    yield parser.parse('test: mov* r1, r2')
    yield parser.parse('0x1000: * r1, [r3, @]')
    yield parser.parse('* @, [*]')
    yield parser.parse('* r1, [r2, @]')
    yield parser.parse('0x200: * r1, [r2], @')
    yield parser.parse('0x200: * r1, [r2], #@:val')
    yield parser.parse('* r1, [r2, @:X]!')
    yield parser.parse('hello: *:opcode r5, {r2-@, r6, *}')
    yield parser.parse('test: * r1, r2, lsl#@:shift')


def test_arm_patterns():
    parser = parsers.create_arm_pattern_parser()
    trees = load_arm_pattern_trees(parser)
    transformer = arm_pattern.ArmPatternTransformer()
    for tree in trees:
        result = transformer.transform(tree)
        print('----------------------------------')
        print(repr(result))
        print('**********************************')
        print(result)


def main():
    test_arm_code()
    test_arm_patterns()


if __name__ == '__main__':
    import sys
    sys.exit(main())
