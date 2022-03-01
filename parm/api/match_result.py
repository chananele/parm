from typing import List


class MatchResult:
    def sub_matches(self, name):
        """

        :param str name:
        :return:
        :rtype: List[MatchResult]
        """
        raise NotImplementedError()

    def sub_match(self, name):
        """

        :param str name:
        :return:
        :rtype: MatchResult
        """
        raise NotImplementedError()

    def __getitem__(self, item):
        raise NotImplementedError()
