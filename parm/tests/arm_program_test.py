from unittest import TestCase
import pytest

from parm.api.exceptions import TooManyMatches, CaptureCollision, ExpectFailure
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

    def test_basic_code_lines(self):
        self.program.add_code_block("""
            0x2000: mov r0, r1
            0x2004: mov r0, r2
            """)
        c = self.program.create_cursor(0x2000)

        env = self.program.env
        env.add_uni_fixture('add_next', lambda cursor: [cursor, cursor.next()])

        p1 = self.program.create_pattern("""
            mov r0, @
            !add_next
            $expect(len(cursors) == 2)
        """)
        p2 = self.program.create_pattern("""
            mov r0, @
            !add_next
            $expect(len(cursors) == 3)
        """)

        c.match(p1)

        with pytest.raises(ExpectFailure):
            c.match(p2)
