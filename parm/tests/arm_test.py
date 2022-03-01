from unittest import TestCase

from parm import parsers
from parm.transformers.arm import *


class ArmTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parsers.create_arm_parser()
        self.transformer = ArmTransformer()

    def _pt(self, *args, **kwargs):
        parsed = self.parser.parse(*args, **kwargs)
        return self.transformer.transform(parsed)

    def test_mov(self):
        expected = Line(Instruction('mov', [Reg('r0'), Immediate(0x10)]))
        assert self._pt('mov r0, #0x10') == expected

    def test_wrong_opcode(self):
        expected = Line(Instruction('ldr', [Reg('r1'), MemAccessOffset(Reg('r1'))]))
        assert self._pt('str r1, [r1]') != expected

    def test_same_address(self):
        expected = Line(Instruction('mov', [Reg('r0'), Immediate(0x10)]), Address(0x300))
        assert self._pt('0x300: mov r0, #0x10') == expected

    def test_different_address(self):
        unexpected = Line(Instruction('mov', [Reg('r0'), Immediate(0x10)]), Address(0x400))
        assert self._pt('0x300: mov r0, #0x10') != unexpected

    def test_ldm(self):
        expected = Line(Instruction('ldm', [Reg('r0'), MemMulti(RegList([Reg('r0'), Reg('r2')]))]))
        assert self._pt('ldm r0, {r0, r2}') == expected

    def test_cases(self):
        expected = Line(Instruction('ldm', [Reg('r0'), MemMulti(RegList([Reg('r0'), Reg('r2')]))]))
        assert self._pt('LDM R0, {R0, R2}') == expected

    def test_ldm_range(self):
        expected = Line(Instruction('ldm', [Reg('r0'), MemMulti(RegList([Reg('r0'), Reg('r1'), Reg('r2')]))]))
        assert self._pt('LDM R0, {R0-R2}') == expected

    def test_conditional(self):
        inst = Instruction('mov', [Reg('r0'), ShiftedReg(Reg('r1'))])
        expected = Line(inst)

        # test ne condition code
        inst.opcode = 'movne'
        assert self._pt('movne r0, r1') == expected

        # test eq condition code
        inst.opcode = 'moveq'
        assert self._pt('moveq r0, r1') == expected

    def test_ldr_simple(self):
        expected = Line(Instruction('ldr', [Reg('r1'), MemAccessOffset(Reg('r1'))]))
        assert self._pt('ldr r1, [r1]') == expected

    def test_blx(self):
        expected = Line(Instruction('blx', Reg('r1')))
        assert self._pt('blx r1') == expected

    def test_bl(self):
        expected = Line(Instruction('bl', Address(0x2000)))
        assert self._pt('bl 0x2000') == expected

    def test_b(self):
        expected = Line(Instruction('b', Address(0x4000)))
        assert self._pt('b 0x4000') == expected

    def test_adc(self):
        expected = Line(Instruction('adc', [Reg('r0'), Reg('r0'), ShiftedReg(Reg('r1'))]))
        assert self._pt('adc r0, r1') == expected

    def test_scaled_sub(self):
        expected = Line(Instruction('sub', [Reg('r0'), Reg('r1'), ShiftedReg(Reg('r2'), 'lsl#6')]))
        assert self._pt('SUB r0, r1, r2, lsl#6') == expected

    def test_scaled_mov(self):
        expected = Line(Instruction('mov', [Reg('r0'), ShiftedReg(Reg('r3'), 'lsl#30')]))
        assert self._pt('mov r0, r3, lsl#30') == expected

    def test_bad_scaled_sub(self):
        expected = Line(Instruction('sub', [Reg('r0'), Reg('r1'), ShiftedReg(Reg('r2'), 'lsl#7')]))
        assert self._pt('SUB r0, r1, r2, lsl#6') != expected

    def test_prefixed_ldr(self):
        expected = Line(
            Instruction('ldrne', [Reg('r0'), MemAccessPreIndexed(Reg('r4'), ShiftedReg(Reg('r1'), 'asr#4'))]))
        assert self._pt('ldrne r0, [r4, r1, asr#4]!') == expected

    def test_ldm_interspersed_range(self):
        expected = Line(Instruction('ldm', [Reg('r0'), MemMulti(
            RegList([Reg('r0'), Reg('r2'), Reg('r3'), Reg('r4'), Reg('r5'), Reg('lr'), Reg('pc')]))]), Address(0x1000))
        assert self._pt('0x1000: ldm r0, {r0, r2-r5, lr, pc}') == expected
