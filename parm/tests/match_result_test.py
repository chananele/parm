import pytest
from unittest import TestCase

from parm.api.exceptions import CaptureCollision
from parm.api.match_result import MatchResult


# noinspection PyMethodMayBeStatic
class MatchResultTest(TestCase):
    def test_to_obj_sanity(self):
        mr = MatchResult()
        mr['a'] = 1
        mr['b'] = 2
        assert mr.to_obj() == dict(a=1, b=2)

    def test_to_json_sanity(self):
        mr = MatchResult()
        mr['a'] = 1
        mr['b'] = 2
        assert mr.to_json() == dict(a=1, b=2)

    def test_non_str_keys(self):
        mr = MatchResult()
        with pytest.raises(ValueError):
            mr[1] = 1

    def test_sub(self):
        mr = MatchResult()
        mr['a'] = 'a'
        scope = mr.new_scope('test')
        scope['b'] = 'b'
        expected = dict(a='a', sub_matches=dict(test=dict(b='b')))
        assert mr.to_obj() == expected
        assert mr.to_json() == expected

    def test_anon_sub(self):
        mr = MatchResult()
        mr['a'] = 'a'
        scope = mr.new_scope()
        scope['b'] = 'b'
        scope = mr.new_scope('test')
        scope['c'] = 'c'
        expected_obj = dict(a='a', sub_matches={
            0: dict(b='b'),
            'test': dict(c='c')
        })
        assert mr.to_obj() == expected_obj
        expected_json = dict(a='a', sub_matches={
            '0': dict(b='b'),
            'test': dict(c='c')
        })
        assert mr.to_json() == expected_json

    def test_overriding(self):
        mr = MatchResult()
        mr['a'] = 'a'
        sub = mr.new_scope()
        with pytest.raises(CaptureCollision):
            sub['a'] = 'b'
