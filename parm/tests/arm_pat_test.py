from unittest import TestCase

import lark.exceptions
import pytest

from parm import parsers
from parm.api.parsing.arm_asm import *
from parm.api.parsing.arm_pat import *


class ArmPatternTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arm_pat_parser = parsers.create_arm_pattern_parser()
        self.arm_parser = parsers.create_arm_parser()
        self.arm_pat_transformer = ArmPatternTransformer()
        self.arm_transformer = ArmTransformer()

    def _pt(self, pattern):
        parsed = self.arm_pat_parser.parse(pattern)
        return self.arm_pat_transformer.transform(parsed)

    def _ct(self, code):
        parsed = self.arm_parser.parse(code)
        return self.arm_transformer.transform(parsed)

    def _pm(self, pattern, code):
        pat = self._pt(pattern)
        c = self._ct(code)
        return pat.match(c)

    def test_blx_tree(self):
        expected = BlockPat([CommandPat(InstructionPat(OpcodePat('blx*'), OperandsPat([RegPat(Reg('r0'))])))])
        assert self._pt('blx* r0') == expected

    def test_bl_tree(self):
        expected = BlockPat([
            AddressPat(Label('test')),
            CommandPat(InstructionPat(OpcodePat('bl'), OperandsPat([AddressPat(WildcardSingle('test'))])))
        ])
        pat = self._pt('test: bl @:test')
        assert pat == expected

    def test_python_pattern(self):
        expected = BlockPat([CommandPat(PythonCodeLine(
            ["match_single(xrefs_to, 'MOV R1, R2')"]
        ))])

        pat = self._pt("""
        % match_single(xrefs_to, 'MOV R1, R2')
        """)
        assert pat == expected

    def test_continued_python_pattern(self):
        # Test line continuation using "\"
        expected = BlockPat([CommandPat(PythonCodeLine(
            ["a = [1, 2, \\\n          3]"]
        ))])
        pat = self._pt("""
        % a = [1, 2, \\
          3]
        """)
        assert pat == expected

        # Only a newline may occur after a "\"
        with pytest.raises(lark.exceptions.UnexpectedCharacters):
            self._pt("""
            % a = [1, 2, \\  # comment
              3]
            """)

        # Test line continuation when in square brackets
        expected = BlockPat([CommandPat(PythonCodeLine(
            ["a = [1, 2,\n          3]"]
        ))])
        pat = self._pt("""
        % a = [1, 2,
          3]
        """)
        assert pat == expected

        # Without "\", the line is finished...
        with pytest.raises(lark.exceptions.UnexpectedCharacters):
            self._pt("""
            % a = "test"
              "test"
            """)

        # Test line continuation when in parentheses
        expected = BlockPat([CommandPat(PythonCodeLine(
            ['a = ("test"\n              "test")']
        ))])
        pat = self._pt("""
            % a = ("test"
              "test")
            """)
        assert pat == expected

    def test_multiline_python_pattern(self):
        expected = BlockPat([CommandPat(PythonCodeLines(
            ["        p = pat('MOV R1, R2')", "        match_single(xrefs_to, p)"]
        ))])

        pat = self._pt("""
        %%
        p = pat('MOV R1, R2')
        match_single(xrefs_to, p)
        %%
        """)
        assert pat == expected

    def test_db(self):
        expected = BlockPat([DataSeq([DataByte(0x10)])])
        pat = self._pt('.db 0x10')
        assert pat == expected

    def test_anchor(self):
        block = BlockPat([DataSeq([DataByte(0x10)]), DataSeq([DataWord(0x200)])])
        pat = self._pt("""
            .db 0x10
          > .dw 0x200
        """)
        assert pat != block
        block.anchor_index = 1
        assert pat == block
