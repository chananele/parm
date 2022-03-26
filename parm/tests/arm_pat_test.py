from unittest import TestCase

import lark.exceptions
import pytest

from parm import parsers
from parm.api.parsing import arm_pat
from parm.api.parsing import arm_asm

from parm.api.parsing.arm_pat import BlockPat, CommandPat, InstructionPat, OperandsPat, OpcodePat, RegPat
from parm.api.parsing.arm_pat import AddressPat, WildcardSingle, Label, PythonCodeLine, PythonCodeLines
from parm.api.parsing.arm_pat import DataSeq, DataByte, DataWord

from parm.api.match_result import MatchResult
from parm.programs.snippet import ArmSnippetProgram


class ArmPatternTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = ArmSnippetProgram()
        self.arm_pat_parser = parsers.create_arm_pattern_parser()
        self.arm_parser = parsers.create_arm_parser()
        self.arm_pat_transformer = arm_pat.ArmPatternTransformer()
        self.arm_transformer = arm_asm.ArmTransformer()

    def create_pattern(self, pattern):
        return self.program.create_pattern(pattern)

    def match_pattern(self, pattern, code):
        cursor = self.program.add_code_block(code)
        pat = self.create_pattern(pattern)
        mr = MatchResult()
        cursor.match(pat, mr)
        return mr

    def test_blx_tree(self):
        expected = BlockPat([CommandPat(InstructionPat(OpcodePat('blx*'), OperandsPat([RegPat(arm_pat.Reg('r0'))])))])
        assert self.create_pattern('blx* r0') == expected

    def test_bl_tree(self):
        expected = BlockPat([
            AddressPat(Label('test')),
            CommandPat(InstructionPat(OpcodePat('bl'), OperandsPat([AddressPat(WildcardSingle('test'))])))
        ])
        pat = self.create_pattern('test: bl @:test')
        assert pat == expected

    def test_python_pattern(self):
        expected = BlockPat([CommandPat(PythonCodeLine(
            ["match_single(xrefs_to, 'MOV R1, R2')"]
        ))])

        pat = self.create_pattern("""
        % match_single(xrefs_to, 'MOV R1, R2')
        """)
        assert pat == expected

    def test_continued_python_pattern(self):
        # Test line continuation using "\"
        expected = BlockPat([CommandPat(PythonCodeLine(
            ["a = [1, 2, \\\n          3]"]
        ))])
        pat = self.create_pattern("""
        % a = [1, 2, \\
          3]
        """)
        assert pat == expected

        # Only a newline may occur after a "\"
        with pytest.raises(lark.exceptions.UnexpectedCharacters):
            self.create_pattern("""
            % a = [1, 2, \\  # comment
              3]
            """)

        # Test line continuation when in square brackets
        expected = BlockPat([CommandPat(PythonCodeLine(
            ["a = [1, 2,\n          3]"]
        ))])
        pat = self.create_pattern("""
        % a = [1, 2,
          3]
        """)
        assert pat == expected

        # Without "\", the line is finished...
        with pytest.raises(lark.exceptions.UnexpectedCharacters):
            self.create_pattern("""
            % a = "test"
              "test"
            """)

        # Test line continuation when in parentheses
        expected = BlockPat([CommandPat(PythonCodeLine(
            ['a = ("test"\n              "test")']
        ))])
        pat = self.create_pattern("""
            % a = ("test"
              "test")
            """)
        assert pat == expected

    def test_multiline_python_pattern(self):
        expected = BlockPat([CommandPat(PythonCodeLines(
            ["        p = pat('MOV R1, R2')", "        match_single(xrefs_to, p)"]
        ))])

        pat = self.create_pattern("""
        %%
        p = pat('MOV R1, R2')
        match_single(xrefs_to, p)
        %%
        """)
        assert pat == expected

    def test_db(self):
        expected = BlockPat([DataSeq([DataByte(0x10)])])
        pat = self.create_pattern('.db 0x10')
        assert pat == expected

    def test_anchor(self):
        block = BlockPat([DataSeq([DataByte(0x10)]), DataSeq([DataWord(0x200)])])
        pat = self.create_pattern("""
            .db 0x10
          > .dw 0x200
        """)
        assert pat != block
        block.anchor_index = 1
        assert pat == block

    def test_match_mov(self):
        asm = 'mov r0, r1'
        pat = 'mov @:reg, r1'
        result = self.match_pattern(pat, asm)
        assert result['reg'].name == 'r0'

    def test_match_push(self):
        asm = 'push {r0, r1}'
        pat = 'push {*:regs}'
        result = self.match_pattern(pat, asm)
        assert result['regs'] == [arm_asm.Reg('r0'), arm_asm.Reg('r1')]
