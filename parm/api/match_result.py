from typing import Mapping, Union, List

_IndexType = Union[int, str]


class MatchResult:

    @property
    def subs(self):
        """
        :rtype: Mapping[_IndexType, List[MatchResult]]
        """
        raise NotImplementedError()

    @property
    def sub(self):
        """
        :rtype: Mapping[_IndexType, MatchResult]
        """
        raise NotImplementedError()

    def __getitem__(self, item):
        raise NotImplementedError()

