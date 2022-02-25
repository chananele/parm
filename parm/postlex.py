from abc import ABC, abstractmethod
from lark.lark import PostLex
from lark.lexer import Token


class ArmSpacer(PostLex, ABC):
    def process(self, stream):

        opcode = None
        previous_token = None

        for token in stream:

            if self.is_opcode_types(token.type):
                assert opcode is None
                opcode = token

            if token.type == self.ws_type:
                if opcode is not None and previous_token is opcode:
                    yield Token(self.injected_type, '')
            else:
                yield token

            previous_token = token

    @abstractmethod
    def is_opcode_types(self, token_type):
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


class Spacer(ArmSpacer):
    ws_type = '_WS'
    injected_type = '_POST_OPCODE'

    def is_opcode_types(self, token_type):
        return token_type.startswith('OPCODE')
