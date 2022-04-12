from parm.api.parsing.arm_asm import Instruction


class Cursor:
    def __init__(self, program):
        self.program = program

    @property
    def instruction(self) -> Instruction:
        raise NotImplementedError()

    @property
    def address(self):
        raise NotImplementedError()

    def read_bytes(self, count) -> bytes:
        raise NotImplementedError()

    def create_data_stream(self):
        return self.program.create_data_stream(self)

    def get_cursor_by_offset(self, offset: int):
        """

        :param offset:
        :return:
        :rtype: Cursor
        """
        raise NotImplementedError()

    def match(self, pattern, match_result, **kwargs):
        raise NotImplementedError()

    def next(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()

    def prev(self):
        """

        :rtype: Cursor
        """
        raise NotImplementedError()
