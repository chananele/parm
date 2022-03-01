from unittest import TestCase

from parm import parsers
from parm.transformers.arm_pattern import *


class ArmPatternTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = parsers.create_arm_pattern_parser()
        self.transformer = ArmPatternTransformer()
