from unittest import TestCase

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

    def test_nested_patterns(self):
        nested = BlockPat([CommandPat(InstructionPat(OpcodePat('MOV'), OperandsPat([
            RegPat(Reg('R1')), ShiftedRegPat(RegPat(Reg('R2')))
        ])))])
        expected = BlockPat([CommandPat(PythonCodeLine(
            ['match_single(xrefs_to, ', nested, ')']
        ))])

        pat = self._pt("""
        !match_single(xrefs_to, ${ MOV R1, R2 })
        """)
        assert pat == expected

    def test_not_nested_patterns(self):
        self._pt("""
        !print('hello')  # ${ bad }
        """)
        self._pt("""
        !print('''${ bad }''')
        """)
        self._pt('''
        !print("""${ bad }""")
        ''')
        self._pt("""
        !print('${ bad }')
        """)
        self._pt('''
        !print("${ bad }")
        ''')

    def test_db(self):
        expected = BlockPat([DataSeq([DataByte(0x1000)])])
        pat = self._pt('.db 0x1000')
        assert pat == expected
