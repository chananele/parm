from unittest import TestCase
import pytest

from parm.api.exceptions import CaptureCollision
from parm.api.match_result import MatchResult
from parm.programs import snippet


class ArmPatternTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = snippet.ArmSnippetProgram()

    def test_blx_match(self):
        self.program.add_code_block('0x2000: blxeq r0')
        pattern = self.program.create_pattern('test: blx*:opcode r0')
        mr = MatchResult()
        with mr.transact():
            result = list(self.program.find_all(pattern, match_result=mr))

        assert mr['opcode'] == 'blxeq'
        assert mr['test'].address == 0x2000
        assert(len(result)) == 1

    def test_collision(self):
        self.program.add_code_block("""
            0x2000: blxeq r0
            0x2008: blxne r0
            """)
        pattern = self.program.create_pattern('test: blx*:opcode r0')
        mr = MatchResult()
        with pytest.raises(CaptureCollision):
            with mr.transact():
                list(self.program.find_all(pattern, match_result=mr))
