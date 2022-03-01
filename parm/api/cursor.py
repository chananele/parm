class Cursor:
    @property
    def address(self):
        raise NotImplementedError()

    def next(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()
