from unittest import TestCase

from parm import parsers
from parm.api.parsing.arm_pat import *


class ArmPatternTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parsers.create_arm_pattern_parser()
        self.transformer = ArmPatternTransformer()

    def _pt(self, *args, **kwargs):
        parsed = self.parser.parse(*args, **kwargs)
        return self.transformer.transform(parsed)
