from lark import Transformer, Token


class OperandsPat:
    def __init__(self, ops):
        self.ops = [o for o in ops if o is not None]

    def __str__(self):
        return ', '.join(str(o) for o in self.ops)

    def __repr__(self):
        return f'OperandsPat({self.ops})'

    def __eq__(self, other):
        if not isinstance(other, OperandsPat):
            return False
        return self.ops == other.ops


class RegPat:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'RegPat({self.value!r})'

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        if not isinstance(other, RegPat):
            return False
        return self.value == other.value


class Reg:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'Reg({self.name!r})'

    def __str__(self):
        return self.name


class WildcardBase:
    @property
    def symbol(self):
        raise NotImplementedError()

    def __init__(self, capture):
        self.capture = capture

    def __repr__(self):
        cap = self.capture
        if cap is None:
            return f'{self.__class__.__name__}()'
        return f'{self.__class__.__name__}({cap!r})'

    def __str__(self):
        cap = self.capture
        if cap is None:
            return self.symbol
        return f'{self.symbol}:{cap}'


class WildcardMulti(WildcardBase):
    symbol = '*'


class WildcardOptional(WildcardBase):
    symbol = '?'


class WildcardSingle(WildcardBase):
    symbol = '@'


class ImmediatePat:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'ImmediatePat({self.value!r})'

    def __str__(self):
        return f'#{self.value}'

    def __eq__(self, other):
        if not isinstance(other, ImmediatePat):
            return False
        return self.value == other.value


class CodeLine:
    @property
    def prefix(self):
        raise NotImplementedError()

    def __init__(self, code):
        self.code = code

    def __repr__(self):
        return f'{self.__class__.__name__}({self.code!r})'

    def __str__(self):
        return f'{self.prefix} {self.code}'

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.code == other.code


class UniCodeLine(CodeLine):
    prefix = '!'


class MultiCodeLine(CodeLine):
    prefix = '$'


class AddressPat:
    pass


class Address(AddressPat):
    def __init__(self, address):
        self.address = address


class Label(AddressPat):
    def __init__(self, label):
        self.label = label


class BlockPat:
    def __init__(self, lines):
        self.lines = lines

    def __repr__(self):
        return f'BlockPat({self.lines!r})'

    def __str__(self):
        return '\n'.join(str(line) for line in self.lines)

    def __eq__(self, other):
        if not isinstance(other, BlockPat):
            return False
        return self.lines == other.lines


class InstructionPat:
    def __init__(self, opcode_pat, operand_pats):
        self.opcode_pat = opcode_pat
        self.operand_pats = operand_pats

    def __repr__(self):
        return f'InstructionPat({self.opcode_pat!r}, {self.operand_pats!r})'

    def __str__(self):
        return f'{self.opcode_pat} {self.operand_pats}'

    def __eq__(self, other):
        if not isinstance(other, InstructionPat):
            return False
        return self.opcode_pat == other.opcode_pat and self.operand_pats == other.operand_pats


class ArmPatternTransformer(Transformer):
    def instruction_line(self, parts):
        (instruction_pat, ) = parts
        return instruction_pat

    def address_pat(self, pat):
        assert isinstance(pat, AddressPat)
        return pat

    def address(self, parts):
        (num, ) = parts
        assert isinstance(num, Token)
        return Address(int(num.value, 0))

    def label(self, parts):
        (name, ) = parts
        assert isinstance(name, Token)
        return Label(name.value)

    def line_pat(self, parts):
        (result, ) = parts
        return result

    def uni_code(self, parts):
        (code, ) = parts
        return UniCodeLine(code)

    def multi_code(self, parts):
        (code, ) = parts
        return MultiCodeLine(code)

    def wildcard_op(self, parts):
        wildcard, operands = parts
        return InstructionPat(wildcard, operands)

    def operands_pat(self, parts):
        return OperandsPat(parts)

    def reg(self, parts):
        (name, ) = parts
        assert isinstance(name, Token)
        return Reg(name.value)

    def reg_pat(self, parts):
        (value, ) = parts
        assert isinstance(value, (Reg, WildcardSingle))
        return RegPat(value)

    def wildcard_m(self, parts):
        (capture, ) = parts
        if capture is not None:
            assert isinstance(capture, Token)
            capture = capture.value
        return WildcardMulti(capture)

    def wildcard_s(self, parts):
        (capture,) = parts
        if capture is not None:
            assert isinstance(capture, Token)
            capture = capture.value
        return WildcardSingle(capture)

    def wildcard_o(self, parts):
        (capture,) = parts
        if capture is not None:
            assert isinstance(capture, Token)
            capture = capture.value
        return WildcardOptional(capture)

    def opcode_wildcard(self, parts):
        (wc, capture) = parts
        assert wc == '*'
        if capture is not None:
            assert isinstance(capture, Token)
            capture = capture.value
        return WildcardMulti(capture)

    def immediate_wildcard(self, parts):
        (wildcard, ) = parts
        assert isinstance(wildcard, WildcardBase)
        return ImmediatePat(wildcard)

    def immediate_value(self, parts):
        (num, ) = parts
        assert isinstance(num, Token)
        return ImmediatePat(num.value)

    def lone_command(self, parts):
        return parts

    def block_pat(self, line_pats):
        lines = []
        for lp in line_pats:
            assert isinstance(lp, list)
            lines.extend(lp)
        return BlockPat(lines)
