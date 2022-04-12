import pytest
from unittest import TestCase
from struct import pack
from construct import Struct, Int16ul, Container, Const

from parm.api.exceptions import TooManyMatches, CaptureCollision, PatternValueMismatch, InvalidAccess
from parm.api.exceptions import ConstructParsingException
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
            % cursor = cursor.next().next()
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
            find_single([prev_instruction, next_instruction], '''
                BL  @:target
                MOV R3, R0
            ''')
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
        % cursor = find_single(candidates, 'MOVNE R0, R2').next()
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
                c.match(self.program.create_pattern('.dd 0x3412, 0x7856'), mr)

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

    def test_anchor_sanity(self):
        self.program.add_code_block("""
        0x2000: mov  r0, r2
        0x2004: mov  r1, r0
        0x2008: bleq 0x2004
        """)
        mr = MatchResult()
        pattern = self.program.create_pattern("""
            mov  r0, r2
          > mov  r1, r0
            bleq @
        """)
        self.program.create_cursor(0x2004).match(pattern, mr)

        with pytest.raises(InvalidAccess):
            self.program.create_cursor(0x2000).match(pattern, mr)

    def test_matchable_generator(self):
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
            !skip_instructions(2)
            bl  @:target
        """)
        c.match(pattern, match_result=mr)
        assert mr['target'].address == 0x8000

    def test_matchable_generator_reverse(self):
        self.program.add_code_block("""
            0x2000: mov r0, r1
                    mov r0, r2
                    ldr r4, [r0]
            0x200C: bl  0x1000
            """)

        mr = MatchResult()
        pattern = self.program.create_pattern("""
            mov r0, @:reg
            !skip_instructions(2)
          > bl  0x1000
        """)

        with pytest.raises(InvalidAccess):
            self.program.create_cursor(0x2000).match(pattern, match_result=mr)

        self.program.create_cursor(0x200C).match(pattern, match_result=mr)
        assert mr['reg'].name == 'r1'

    def test_mixed_code_and_data_reverse(self):
        self.program.add_code_block("""
        0x2008: mov r0, r2
        0x200C: mov r1, r0
        0x2010:
        """)
        self.program.add_data_block(0x2000, pack('<II', 0xDEADBEEF, 0x1337))
        mr = MatchResult()
        good_pattern = self.program.create_pattern("""
            .dd 0xDEADBEEF
            .dw 0x1337, 0
          > mov r0, r2
            mov r1, r0
        """)
        bad_pattern = self.program.create_pattern("""
            .dd 0xDEADBEEF
            .dw 0x1338, 0
          > mov r0, r2
        """)

        c = self.program.create_cursor(0x2008)
        c.match(good_pattern, mr)
        with pytest.raises(PatternValueMismatch):
            c.match(bad_pattern, mr)

        with pytest.raises(PatternValueMismatch):
            self.program.create_cursor(0x2004).match(good_pattern, mr)

        with pytest.raises(InvalidAccess):
            self.program.create_cursor(0x200C).match(good_pattern, mr)

    def test_goto_next(self):
        self.program.add_code_block("""
        0x1000: mov r5, r0
                blxeq r1
                mov r0, r4
                bleq  0x1000
                mov r0, r5
                bleq  0x2000
        """)
        pattern = self.program.create_pattern("""
        mov @:reg, r0
        % goto_next('''
            mov r0, @:reg
            bleq @:target 
        ''')
        """)
        mr = MatchResult()
        self.program.create_cursor(0x1000).match(pattern, match_result=mr)
        assert mr['target'].address == 0x2000

    def test_goto_after_next(self):
        self.program.add_code_block("""
        0x1000: mov   r5, r0
                mov   r3, r0
                blxeq r1
                mov   r0, r4
                bleq  0x1000
                mov   r0, r5
                bleq  0x2000
                b     0x3000
                mov   r0, r3
                bleq  0x8000
                adc   r4, r9
        """)

        mr = MatchResult()
        self.program.find_first("""
        mov @:reg, r0
        % goto_after_next('''
            mov r0, @:reg
            bleq @:target 
        ''')
        """, mr)
        assert mr['target'].address == 0x2000

        mr = MatchResult()
        self.program.find_first("""
        mov @:reg, r0
        % goto_after_next(''' 
            mov r0, @:reg
            bleq @:target 
        ''')
        adc r4, @
        """, mr)
        assert mr['target'].address == 0x8000

    def test_old_embedding_syntax(self):
        self.program.add_code_block("0x1000: mov r5, r0")
        mr = MatchResult()
        with pytest.raises(SyntaxError):
            self.program.find_first("""
            % goto_after_next(${mov r5, r0})
            """, mr)

    def test_goto(self):
        self.program.add_code_block("""
            0x2000: mov r0, r1
                    mov r0, r2
                    ldr r4, [r0]
                    bl  0x1000
            0x2010: mov r5, r0
            """)
        c = self.program.create_cursor(0x2000)

        mr = MatchResult()
        pattern = self.program.create_pattern("""
            mov r0, @
            % goto(cursor.next().next())
            bl  @:target
        """)
        c.match(pattern, match_result=mr)
        assert mr['target'].address == 0x1000

        mr = MatchResult()
        pattern = self.program.create_pattern("""
            mov r0, @
            % goto(0x2010)
            mov @:reg, r0
        """)
        c.match(pattern, match_result=mr)
        assert mr['reg'].name == 'r5'

    def test_data_obj(self):
        self.program.add_data_block(0x1000, pack('<IHHI', 0, 0xDEAD, 0xBEEF, 0xAABBCCDD))
        mr = MatchResult()
        pattern = self.program.create_pattern("""
            .obj test:$obj_type
        """)
        self.program.create_cursor(0x1004).match(pattern, mr, obj_type=Struct(a=Int16ul, b=Int16ul))
        test = mr['test']
        assert isinstance(test, Container)
        assert test['a'] == 0xDEAD and test['b'] == 0xBEEF

        obj_type = Struct(x=Const(b'\xAD\xDE'), y=Int16ul)
        pattern = self.program.create_pattern("""
            .obj test:$obj_type
          > .dd @:other
        """)

        with pytest.raises(InvalidAccess):
            mr = MatchResult()
            self.program.create_cursor(0x1000).match(pattern, mr, obj_type=obj_type)

        with pytest.raises(ConstructParsingException):
            mr = MatchResult()
            self.program.create_cursor(0x1004).match(pattern, mr, obj_type=obj_type)

        mr = MatchResult()
        self.program.create_cursor(0x1008).match(pattern, mr, obj_type=obj_type)
        assert mr['test']['y'] == 0xBEEF
        assert mr['other'] == 0xAABBCCDD

    def test_anonymous_data_obj(self):
        self.program.add_data_block(0x1000, pack('<HHHH', 0xDEAD, 0, 0xBEEF, 0))
        mr = MatchResult()
        obj_type = Struct(a=Const(b'\xEF\xBE'), b=Int16ul)
        pattern = self.program.create_pattern("""
            .obj $obj_type
        """)

        with pytest.raises(ConstructParsingException):
            self.program.create_cursor(0x1000).match(pattern, mr, obj_type=obj_type)

        self.program.create_cursor(0x1004).match(pattern, mr, obj_type=obj_type)
