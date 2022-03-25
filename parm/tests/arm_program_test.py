import pytest
from unittest import TestCase
from struct import pack

from parm.api.exceptions import TooManyMatches, CaptureCollision, PatternValueMismatch
from parm.api.match_result import MatchResult
from parm.api.parsing.arm_asm import Reg
from parm.programs import snippet


class ArmPatternTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = snippet.ArmSnippetProgram()

    def test_blx_match(self):
        self.program.add_code_block('0x2000: blxeq r0')
        pattern = self.program.create_pattern('test: blx*:opcode r0')
        mr = MatchResult()
        result = list(self.program.find_all(pattern, match_result=mr))

        ms = mr.subs[0]
        assert ms[0]['opcode'] == 'blxeq'
        assert ms[0]['test'].address == 0x2000
        assert(len(result)) == 1

    def test_find_single(self):
        self.program.add_code_block("""
            0x2000: blxeq r0
            0x2008: blxne r1
            """)
        pattern = self.program.create_pattern('test: blx*:opcode r1')
        mr = MatchResult()
        with mr.transact():
            self.program.find_single(pattern, match_result=mr)
        assert mr['test'].address == 0x2008

    def test_too_many_matches(self):
        self.program.add_code_block("""
            0x2000: blxeq r0
            0x2008: blxne r0
            """)
        pattern = self.program.create_pattern('test: blx*:opcode r0')
        mr = MatchResult()
        with pytest.raises(TooManyMatches):
            with mr.transact():
                self.program.find_single(pattern, match_result=mr)

    def test_capture_collision(self):
        self.program.add_code_block('0x1000: bl 0x2000')
        self.program.add_code_block('0x3000: bl 0x3000')
        self.program.add_code_block('0x4000: bl 0x4000')
        pattern = self.program.create_pattern('test: bl @:test')
        mr = MatchResult()
        with pytest.raises(CaptureCollision):
            with mr.transact():  # Required to ensure the failed match does not dirty the match_result...
                self.program.create_cursor(0x1000).match(pattern, match_result=mr)

        self.program.create_cursor(0x3000).match(pattern, match_result=mr)
        assert mr['test'].address == 0x3000

        with pytest.raises(CaptureCollision):
            # Even though it matches the pattern, "test" is already bound to 0x3000
            self.program.create_cursor(0x4000).match(pattern, match_result=mr)

    def test_code_line(self):
        self.program.add_code_block("""
            0x2000: mov r0, r1
                    mov r0, r2
                    ldr r4, [r0]
                    bl  0x8000
            """)
        c = self.program.create_cursor(0x2000)

        mr = MatchResult()
        pattern = self.program.create_pattern("""
            mov r0, @
            % skip_instructions(2)
            bl  @:target
        """)
        c.match(pattern, match_result=mr)
        assert mr['target'].address == 0x8000

    def test_nested_pattern(self):
        self.program.add_code_block("""
            0x2000: mov r0, r1
                    mov r0, r2
                    bl  0x6000
                    mov r3, r0
            """)
        c = self.program.create_cursor(0x2000)

        mr = MatchResult()
        pattern = self.program.create_pattern("""
            mov r0, r1
            %%
            find_single([prev_instruction, next_instruction], ${
                BL  @:target
                MOV R3, R0
            })
            %%
        """)
        c.match(pattern, match_result=mr)
        assert mr['target'].address == 0x6000

    def test_object_injection(self):
        self.program.add_code_block("""
            mov   r0, r1
            movne r0, r2
            bl    0x10000
            ldr   r3, [r0]
            """)
        mr = MatchResult()
        pattern = self.program.create_pattern("""
        % cursor = find_single(candidates, ${ MOVNE R0, R2 }).next()
        BL @:target
        """)
        self.program.match(pattern, mr, candidates=self.program.asm_cursors)
        assert mr['target'].address == 0x10000

    def test_data_bytes(self):
        self.program.add_data_block(0x1000, b'\xAA\xBB')
        mr = MatchResult()
        pattern = self.program.create_pattern("""
        .db 0xAA, 0xBB
        """)
        self.program.create_cursor(0x1000).match(pattern, mr)

    def test_data_words(self):
        self.program.add_data_block(0x1000, b'\xAA\xBB\xCC\xDD\xEE\xFF')
        mr = MatchResult()
        pattern = self.program.create_pattern("""
        .dw 0xBBAA, 0xDDCC
        .dw 0xFFEE
        """)
        self.program.create_cursor(0x1000).match(pattern, mr)

    def test_data_dwords(self):
        self.program.add_data_block(0x1000, pack('<II', 0x1234, 0x5678))
        mr = MatchResult()
        pattern = self.program.create_pattern("""
        .dd 0x1234, 0x5678
        """)
        c = self.program.create_cursor(0x1000)
        c.match(pattern, mr)

        with pytest.raises(PatternValueMismatch):
            with mr.transact():
                c.match(self.program.create_pattern('.dd 0x3412, 0x7856'))

    def test_data_qwords(self):
        self.program.add_data_block(0x1000, pack('<QQ', 0xDEAD, 0xBEEF))
        mr = MatchResult()
        pattern = self.program.create_pattern("""
        .dq 0xDEAD, 0xBEEF
        """)
        self.program.create_cursor(0x1000).match(pattern, mr)

    def test_mixed_code_and_data(self):
        self.program.add_code_block("""
        0x2000: mov r0, r2
        0x2004: mov r1, r0
        0x2008:
        """)
        self.program.add_data_block(0x2008, pack('<I', 0xDEADBEEF))
        mr = MatchResult()
        pattern = self.program.create_pattern("""
        mov @:reg, r2
        mov r1, @:reg
        .dd 0xDEADBEEF
        """)
        self.program.create_cursor(0x2000).match(pattern, mr)
        reg = mr['reg']
        assert isinstance(reg, Reg)
        assert reg.name == 'r0'
