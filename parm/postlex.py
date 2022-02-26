from abc import ABC, abstractmethod
from lark.lark import PostLex
from lark.lexer import Token


class Spacer(PostLex, ABC):
    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug

    def process(self, stream):

        opcode = None
        previous_token = None
        injected = False

        for token in stream:
            if self.is_opcode_type(token.type):
                if opcode is not None:
                    assert self.is_operand_type(opcode)
                else:
                    opcode = token

            if token.type == self.ws_type:
                if opcode is not None and previous_token is opcode:
                    assert not injected, 'Detected multiple opcodes!'
                    yield Token(self.injected_type, '')
                    injected = True
            else:
                yield token

            previous_token = token

    @abstractmethod
    def is_opcode_type(self, token_type):
        raise NotImplementedError()

    @abstractmethod
    def is_operand_type(self, token_type):
        raise NotImplementedError()

    @property
    @abstractmethod
    def ws_type(self):
        raise NotImplementedError()

    @property
    @abstractmethod
    def injected_type(self):
        raise NotImplementedError()

    @property
    def always_accept(self):
        result = (self.ws_type, )
        return result


class PatternSpacer(Spacer, ABC):
    @property
    @abstractmethod
    def label_type(self):
        raise NotImplementedError()

    def process(self, stream):

        opcode = None
        previous_token = None
        injected = False

        colon = None
        label = False

        for token in stream:

            if self.is_opcode_type(token.type):
                if opcode is not None:
                    assert self.is_operand_type(opcode)
                else:
                    opcode = token

            if previous_token is opcode:
                if token.value == ':':
                    colon = token

            if previous_token is colon:
                if token.type == self.label_type:
                    label = token

            if token.type == self.ws_type:
                should_inject = False
                if opcode is not None and previous_token is opcode:
                    should_inject = True
                if label is not None and previous_token is label:
                    should_inject = True
                if should_inject:
                    assert not injected, 'Detected multiple opcodes!'
                    yield Token(self.injected_type, '')
                    injected = True
            else:
                yield token

            previous_token = token
