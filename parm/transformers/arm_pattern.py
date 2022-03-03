from lark import Transformer, Token

from parm.utils import indent


class MemSinglePatBase:
    def __init__(self, base, offset=None):
        self.base = base
        self.offset = offset

        self.parts = [p for p in (base, offset) if p is not None]

    def __repr__(self):
        return f'{self.__class__.__name__}({", ".join([repr(o) for o in self.parts])})'

    def __str__(self):
        raise NotImplementedError()


class MemSinglePat(MemSinglePatBase):
    def __str__(self):
        return f'[{", ".join([str(o) for o in self.parts])}]'


class MemSinglePrePat(MemSinglePatBase):
    def __str__(self):
        return f'[{", ".join([str(o) for o in self.parts])}]!'


class MemSinglePostPat(MemSinglePatBase):
    def __init__(self, base, offset):
        assert offset is not None
        super().__init__(base, offset)

    def __str__(self):
        return f'[{self.base}], {self.offset}'


class ContainerBase:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.value == other.value


class MemOffsetPat(ContainerBase):
    pass


class ShiftedRegPat:
    def __init__(self, reg_pat, shift_pat=None):
        self.reg_pat = reg_pat
        self.shift_pat = shift_pat

    def __str__(self):
        if self.shift_pat is None:
            return str(self.reg_pat)
        return f'{self.reg_pat}, {self.shift_pat}'

    def __repr__(self):
        ps = [str(self.reg_pat)]
        if self.shift_pat is not None:
            ps.append(str(self.shift_pat))
        return f'ShiftedRegPat({", ".join(ps)})'


class MemMultiPat:
    def __init__(self, reg_list):
        self.reg_list = reg_list

    def __repr__(self):
        return f'MemMultiPat({self.reg_list!r})'

    def __str__(self):
        return '{{{}}}'.format(', '.join(str(r) for r in self.reg_list))


class RegRangePat:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return f'RegRangePat({self.start!r}, {self.end!r})'

    def __str__(self):
        return f'{self.start}-{self.end}'


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


class RegPat(ContainerBase):
    pass


class Reg(ContainerBase):
    pass


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


class AddressPat(ContainerBase):
    pass


class Address:
    def __init__(self, address):
        self.address = address

    def __repr__(self):
        return f'Address({self.address})'

    def __str__(self):
        return f'0x{self.address:X}'


class Label(ContainerBase):
    pass


class BlockPat:
    def __init__(self, lines):
        self.lines = lines

    def __repr__(self):
        return f'BlockPat({self.lines!r})'

    def __str__(self):
        line_strs = []
        for line in self.lines:
            if isinstance(line, AddressPat):
                line_strs.append(f'{line}:')
            elif isinstance(line, InstructionPat):
                line_strs.append(indent(str(line)))
            else:
                raise TypeError(f'Invalid line of type {type(line)}')

        return '\n'.join(line_strs)

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
        assert isinstance(pat, (Address, Label))
        return AddressPat(pat)

    def address(self, parts):
        (num, ) = parts
        assert isinstance(num, Token)
        return AddressPat(Address(int(num.value, 0)))

    def label(self, parts):
        (name, ) = parts
        assert isinstance(name, Token)
        return AddressPat(Label(name.value))

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

    def addressed_command(self, parts):
        return parts

    def block_pat(self, line_pats):
        lines = []
        for lp in line_pats:
            assert isinstance(lp, list), type(lp)
            lines.extend(lp)
        return BlockPat(lines)

    def _mem_multi_pat_1(self, parts):
        (value, ) = parts
        assert isinstance(value, (RegPat, RegRangePat))
        return value

    def _mem_multi_pat_2(self, parts):
        assert all(isinstance(p, (RegPat, RegRangePat, WildcardMulti)) for p in parts)
        return parts

    def mem_multi_pat(self, parts):
        assert all(isinstance(p, (RegPat, RegRangePat, WildcardMulti)) for p in parts)
        return MemMultiPat(parts)

    def reg_range_pat(self, parts):
        start, end = parts
        return RegRangePat(start, end)

    def mem_offset_pat(self, parts):
        (value, ) = parts
        return MemOffsetPat(value)

    def shifted_reg_pat(self, parts):
        reg_pat, shift_pat = parts
        return ShiftedRegPat(reg_pat, shift_pat)

    shifted_reg_offset_pat = shifted_reg_pat

    def mem_single_wildcard_m(self, parts):
        (wc, ) = parts
        return MemSinglePat(wc)

    def mem_single_wildcard_m_pre(self, parts):
        (wc, ) = parts
        return MemSinglePrePat(wc)

    def mem_single_wildcard_m_post(self, parts):
        wc, offset = parts
        return MemSinglePostPat(wc, offset)

    def mem_single_reg(self, parts):
        reg_pat, offset = parts
        return MemSinglePat(reg_pat, offset)

    def mem_single_reg_pre(self, parts):
        reg_pat, offset = parts
        return MemSinglePrePat(reg_pat, offset)

    def mem_single_reg_post(self, parts):
        reg_pat, offset = parts
        return MemSinglePostPat(reg_pat, offset)
