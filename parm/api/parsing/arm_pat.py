from typing import Iterable

from fnmatch import fnmatch
from functools import wraps
from lark import Transformer, Token

from parm.api.parsing import arm
from parm.api.parsing.utils import indent
from parm.api.common import default_match_result
from parm.api.exceptions import PatternMismatchException, OperandsExhausted
from parm.api.exceptions import PatternTypeMismatch, PatternValueMismatch, NoMatches, NotAllOperandsMatched
from parm.api.match_result import MatchResult
from parm.api.env import Env
from parm.api.cursor import Cursor
from parm.api.pattern import LineUniPattern, LineMultiPattern, BlockPattern


def _consume_list(lst: list, operands: list, env: Env, match_result: MatchResult, complete):
    def _completer_gen(i):
        try:
            o = lst[i + 1]
        except IndexError:
            return complete

        def completer(remaining):
            o.consume(remaining, env, match_result, _completer_gen(i + 1))

        return completer

    try:
        op = lst[0]
    except IndexError:
        complete(operands)
    else:
        op.consume(operands, env, match_result, _completer_gen(0))


def _single_consumer(func):
    @wraps(func)
    def decorator(self, operands: list, env: Env, match_result: MatchResult, complete):
        try:
            op0 = operands[0]
        except IndexError:
            raise OperandsExhausted(self)
        func(self, op0, env, match_result)
        complete(operands[1:])

    return decorator


def _expect_done(rem):
    if rem:
        raise NotAllOperandsMatched(rem)


class OpcodePat:
    def __init__(self, name, capture=None):
        self.name = name
        self.capture = capture

    def __repr__(self):
        if self.capture is None:
            return f'OpcodePat({self.name!r})'
        return f'OpcodePat({self.name!r}, {self.capture!r})'

    def __str__(self):
        if self.capture is None:
            return self.name
        return f'{self.name}:{self.capture}'

    def __eq__(self, other):
        if not isinstance(other, OpcodePat):
            return False
        return self.name == other.name and self.capture == other.capture

    def match(self, opcode, _e: Env, match_result: MatchResult):
        if not isinstance(opcode, str):
            raise PatternTypeMismatch(self.name, opcode)
        if not fnmatch(opcode, self.name):
            raise PatternValueMismatch(self.name, opcode)
        match_result[self.capture] = opcode


class ShiftPat:
    def __init__(self, op, val):
        self.op = op
        self.val = val

    def __repr__(self):
        return f'ShiftPat({self.op!r}, {self.val!r})'

    def __str__(self):
        return f'{self.op}#{self.val}'


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


class CommandPat(ContainerBase):
    @default_match_result
    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        return self.value.match(cursors, env, match_result)


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

    @_single_consumer
    def consume(self, op, env: Env, match_result: MatchResult):
        if isinstance(op, arm.ShiftedReg):
            self.reg_pat.consume([op.reg], env, match_result, _expect_done)
            if self.shift_pat is None:
                if op.shift is not None:
                    raise PatternValueMismatch(self, op)
            else:
                self.shift_pat.consume([op.shift], env, match_result, _expect_done)
        elif isinstance(op, arm.Reg):
            if self.shift_pat is not None:
                self.shift_pat.consume([None], env, match_result, _expect_done)
            self.reg_pat.consume([op], env, match_result, _expect_done)
        else:
            raise PatternTypeMismatch(self, op)


class MemMultiPat:
    def __init__(self, reg_list):
        self.reg_list = reg_list

    def __repr__(self):
        return f'MemMultiPat({self.reg_list!r})'

    def __str__(self):
        return '{{{}}}'.format(', '.join(str(r) for r in self.reg_list))

    @_single_consumer
    def consume(self, op, env: Env, match_result):
        if not isinstance(op, arm.MemMulti):
            raise PatternTypeMismatch(self, op)
        _consume_list(self.reg_list, op.reg_list, env, match_result, _expect_done)


class RegRangePat:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return f'RegRangePat({self.start!r}, {self.end!r})'

    def __str__(self):
        return f'{self.start}-{self.end}'

    def consume(self, operands: list, env: Env, match_result: MatchResult, complete):
        try:
            s = operands[0]
        except IndexError:
            raise OperandsExhausted(self)

        if not isinstance(s, arm.Reg):
            raise PatternTypeMismatch(self, s)

        self.start.consume([s], env, match_result, _expect_done)
        s_index = arm.REG_INDEX[s.name]

        for i, o in enumerate(operands[1:]):
            if not isinstance(o, arm.Reg):
                raise PatternTypeMismatch(self, o)
            if arm.REG_INDEX[o.name] != s_index + i + 1:
                break
            try:
                with match_result.transact():
                    self.end.consume([o], env, match_result, _expect_done)
                    complete(operands[i + 2:])
                    return
            except PatternMismatchException:
                pass

        raise PatternValueMismatch(self, operands)


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

    @default_match_result
    def match(self, operands: list, env: Env, match_result: MatchResult):
        _consume_list(self.ops, operands, env, match_result, _expect_done)


class IntegerVal(ContainerBase):
    @_single_consumer
    def consume(self, op, _):
        if not isinstance(op, int):
            raise PatternTypeMismatch(self.value, op)
        if op != self.value:
            raise PatternValueMismatch(self.value, op)


class RegPat(ContainerBase):
    def consume(self, operands: list, env: Env, match_result: MatchResult, complete):
        self.value.consume(operands, env, match_result, complete)


class Reg(ContainerBase):
    @_single_consumer
    @default_match_result
    def consume(self, op, _: Env, match_result: MatchResult):
        if not isinstance(op, arm.Reg):
            raise PatternTypeMismatch(self.value, op)
        if self.value.lower() != op.name.lower():
            raise PatternValueMismatch(self.value, op)


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

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        if self.capture != other.capture:
            return False
        return True

    @default_match_result
    def match(self, value, _e: Env, match_result: MatchResult):
        match_result[self.capture] = value


class WildcardMulti(WildcardBase):
    symbol = '*'

    @default_match_result
    def consume(self, operands, _e: Env, match_result: MatchResult, complete):
        for i in range(len(operands) + 1):
            with match_result.transact():
                complete(operands[i:])
                match_result[self.capture] = operands[:i]
        raise NoMatches()


class WildcardOptional(WildcardBase):
    symbol = '?'

    @default_match_result
    def consume(self, operands: list, _e: Env, match_result: MatchResult, complete):
        try:
            op0 = operands[0]
        except IndexError:
            pass
        else:
            try:
                with match_result.transact():
                    match_result[self.capture] = op0
                    complete(operands[1:])
                    return
            except PatternMismatchException:
                pass
        match_result[self.capture] = None
        complete(operands)


class WildcardSingle(WildcardBase):
    symbol = '@'

    @_single_consumer
    def consume(self, op, _e: Env, match_result: MatchResult):
        match_result[self.capture] = op


class ImmediatePat:
    def __init__(self, value):
        self.value = value

    @_single_consumer
    def consume(self, op, env: Env, match_result: MatchResult):
        if not isinstance(op, arm.Immediate):
            raise PatternTypeMismatch(self, op)

        self.value.consume([op.value], env, match_result, _expect_done)

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
        self._code = code

    @property
    def code(self):
        return self._code

    def __repr__(self):
        return f'{self.__class__.__name__}({self.code!r})'

    def __str__(self):
        return f'{self.prefix}{self.code}'

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.code == other.code


class UniCodeLine(CodeLine, LineUniPattern):
    prefix = '!'


class MultiCodeLine(CodeLine, LineMultiPattern):
    prefix = '$'


class AddressPat(ContainerBase):
    def __init__(self, value):
        super().__init__(value)

    @default_match_result
    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        for cursor in cursors:
            self.value.match(cursor.address, env, match_result)
        return cursors

    @_single_consumer
    def consume(self, op, env: Env, match_result: MatchResult):
        self.value.match(op, env, match_result)


class Address:
    def __init__(self, address):
        self.address = address

    def __repr__(self):
        return f'Address({self.address})'

    def __str__(self):
        return f'0x{self.address:X}'

    def match(self, address, _e: Env, _m: MatchResult):
        if address != self.address:
            raise PatternValueMismatch(self.address, address)


class Label(ContainerBase):
    def match(self, address, _e: Env, match_result: MatchResult):
        match_result[self.value] = address


class BlockPat(BlockPattern):
    def __init__(self, lines):
        self._lines = lines

    @property
    def lines(self):
        return self._lines

    def __repr__(self):
        return f'BlockPat({self.lines!r})'

    def __str__(self):
        line_strs = []
        for line in self.lines:
            if isinstance(line, AddressPat):
                line_strs.append(f'{line}:')
            elif isinstance(line, CommandPat):
                line_strs.append(indent(str(line)))
            else:
                raise TypeError(f'Invalid line of type {type(line)}, {line}')

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

    @default_match_result
    def match(self, cursors: Iterable[Cursor], env: Env, match_result: MatchResult) -> Iterable[Cursor]:
        next_cursors = []
        for c in cursors:
            inst = c.instruction
            self.opcode_pat.match(inst.opcode, env, match_result)
            self.operand_pats.match(inst.operands, env, match_result)
            next_cursors.append(c.next())
        return next_cursors


class ArmPatternTransformer(Transformer):
    def opcode_wildcard(self, parts):
        (capture,) = parts
        return OpcodePat('*', capture)

    def _opcode_pat(self, parts):
        pat, capture = parts
        assert isinstance(pat, Token)
        return OpcodePat(pat.value, capture)

    approx_mov = _opcode_pat
    approx_arithmetic = _opcode_pat
    approx_branch_rel = _opcode_pat
    approx_branch_ind = _opcode_pat

    def _exact_opcode(self, parts):
        (pat,) = parts
        assert isinstance(pat, Token)
        return OpcodePat(pat.value)

    exact_mov = _exact_opcode
    exact_arithmetic = _exact_opcode
    exact_branch_rel = _exact_opcode
    exact_branch_ind = _exact_opcode

    def instruction_line(self, parts):
        (instruction_pat,) = parts
        return CommandPat(instruction_pat)

    def instruction_pat(self, parts):
        opcode, operands = parts
        assert isinstance(opcode, OpcodePat), opcode
        return InstructionPat(opcode, operands)

    def line_address_pat(self, pat):
        assert isinstance(pat, (Address, Label))
        return AddressPat(pat)

    def address_pat(self, parts):
        (pat,) = parts
        assert isinstance(pat, (Address, WildcardSingle))
        return AddressPat(pat)

    def address(self, parts):
        (num,) = parts
        assert isinstance(num, Token)
        return AddressPat(Address(int(num.value, 0)))

    def label(self, parts):
        (name,) = parts
        assert isinstance(name, Token)
        return AddressPat(Label(name.value))

    def line_pat(self, parts):
        (result,) = parts
        return result

    def uni_code(self, parts):
        (code,) = parts
        return CommandPat(UniCodeLine(code))

    def multi_code(self, parts):
        (code,) = parts
        return CommandPat(MultiCodeLine(code))

    def capture_opt(self, parts):
        (cap,) = parts
        if cap is not None:
            assert isinstance(cap, Token)
            cap = cap.value
        return cap

    def operands_pat(self, parts):
        return OperandsPat(parts)

    mov_operands_pat = operands_pat
    arithmetic_operands_pat = operands_pat
    branch_rel_operands_pat = operands_pat
    branch_ind_operands_pat = operands_pat

    def reg(self, parts):
        (name,) = parts
        assert isinstance(name, Token)
        return Reg(name.value)

    def reg_pat(self, parts):
        (value,) = parts
        assert isinstance(value, (Reg, WildcardSingle))
        return RegPat(value)

    def wildcard_m(self, parts):
        (capture,) = parts
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

    def immediate_wildcard(self, parts):
        (wildcard,) = parts
        assert isinstance(wildcard, WildcardBase)
        return ImmediatePat(wildcard)

    def immediate_value(self, parts):
        (num,) = parts
        assert isinstance(num, Token)
        return ImmediatePat(IntegerVal(int(num.value, 0)))

    def lone_command(self, parts):
        return parts

    def lone_address(self, parts):
        return parts

    def addressed_command(self, parts):
        return parts

    def block_pat(self, line_pats):
        lines = []
        for lp in line_pats:
            assert isinstance(lp, list), lp
            lines.extend(lp)
        return BlockPat(lines)

    def _mem_multi_pat_1(self, parts):
        (value,) = parts
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
        (value,) = parts
        return MemOffsetPat(value)

    def shift_op(self, parts):
        (op,) = parts
        assert isinstance(op, Token)
        return op.value

    def shift_op_wildcard(self, value):
        assert isinstance(value, WildcardSingle)
        return value

    def shift_val(self, parts):
        (val,) = parts
        assert isinstance(val, Token)
        return val.value

    def shift_val_wildcard(self, parts):
        (value,) = parts
        assert isinstance(value, WildcardSingle), value
        return value

    def shift_pat(self, parts):
        op, val = parts
        return ShiftPat(op, val)

    def shifted_reg_pat(self, parts):
        reg_pat, shift_pat = parts
        return ShiftedRegPat(reg_pat, shift_pat)

    shifted_reg_offset_pat = shifted_reg_pat

    def mem_single_wildcard_m(self, parts):
        (wc,) = parts
        return MemSinglePat(wc)

    def mem_single_wildcard_m_pre(self, parts):
        (wc,) = parts
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
