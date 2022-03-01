from unittest import TestCase

from parm import parsers
from parm.transformers.arm import *


class ArmParseTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parsers.create_arm_parser()
        self.transformer = ArmTransformer()

    def _pt(self, *args, **kwargs):
        parsed = self.parser.parse(*args, **kwargs)
        return self.transformer.transform(parsed)

    def test_transformations(self):
        expected = Line(Instruction('ldm', [Operands(Reg('r0'), MemMulti(
            RegList([Reg('r0'), Reg('r2'), Reg('r3'), Reg('r4'), Reg('r5'), Reg('lr'), Reg('pc')])))]), Address(0x1000))
        assert self._pt('0x1000: ldm r0, {r0, r2-r5, lr, pc}') == expected


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
    transformer = ArmTransformer()
    for tree in trees:
        result = transformer.transform(tree)
        print(repr(result))


def main():
    test_arm_code()


if __name__ == '__main__':
    import sys

    sys.exit(main())
