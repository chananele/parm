from pathlib import Path
from unittest import TestCase

from parm.api.match_result import MatchResult
from parm.programs.capstone import CapstoneProgram

SNIPPETS_DIR = Path(__file__).parent / "snippets"


def _is_excluded_file(f: Path):
    if f.is_dir():
        return True
    if f.suffix in ('.id0', '.id1', '.id2', '.nam', '.til', '.py'):
        return True
    return False


def _load_programs():
    return {
        snippet.name: CapstoneProgram.load_arm_elf(snippet)
        for snippet in SNIPPETS_DIR.iterdir()
        if not _is_excluded_file(snippet)
    }


class CapstoneProgramTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.programs = _load_programs()

    def test_find_single(self):
        prg = self.programs['mul']
        pattern = prg.create_pattern('test: bne #0x1043c')
        mr = MatchResult()
        prg.find_single(pattern, match_result=mr)
        assert mr['test'].address == 0x10458
