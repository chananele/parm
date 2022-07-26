from abc import ABC
from typing import List, Literal

from fnmatch import fnmatch
from functools import wraps
from collections import OrderedDict
from construct import ConstructError

from lark import Transformer, Token

from parm.api.matchable import Matchable
from parm.api.parsing import arm_asm
from parm.api.parsing.utils import indent
from parm.api.exceptions import PatternMismatchException, OperandsExhausted, ConstructParsingException
from parm.api.exceptions import PatternTypeMismatch, PatternValueMismatch, NoMatches, NotAllOperandsMatched
from parm.api.execution_context import ExecutionContext
from parm.api.pattern import CodeLineBase, CodeLinePatternBase, BlockPattern, CodeLineMatchableGenerator


def _consume_list(lst: list, operands: list, ctx: ExecutionContext, complete):
    def _completer_gen(i):
        try:
            o = lst[i + 1]
        except IndexError:
            return complete

        def completer(remaining):
            o.consume(remaining, ctx, _completer_gen(i + 1))

        return completer

    try:
        op = lst[0]
    except IndexError:
        complete(operands)
    else:
        op.consume(operands, ctx, _completer_gen(0))


def _single_consumer(func):
    @wraps(func)
    def decorator(self, operands: list, ctx: ExecutionContext, complete):
        try:
            op0 = operands[0]
        except IndexError:
            raise OperandsExhausted(self)
        func(self, op0, ctx)
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
        return self.name.lower() == other.name.lower() and self.capture == other.capture

    def match(self, opcode, ctx: ExecutionContext, **_kwargs):
        if not isinstance(opcode, str):
            raise PatternTypeMismatch(self.name, opcode)
        if not fnmatch(opcode.lower(), self.name.lower()):
            raise PatternValueMismatch(self.name, opcode)
        ctx.match_result[self.capture] = opcode


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


class CommandPat(ContainerBase, Matchable):
    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        return self.value.match(ctx, **kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        return self.value.match_reverse(ctx, **kwargs)


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
        ps = [f'{self.reg_pat!r}']
        if self.shift_pat is not None:
            ps.append(f'{self.shift_pat!r}')
        return f'ShiftedRegPat({", ".join(ps)})'

    def __eq__(self, other):
        if isinstance(other, ShiftedRegPat):
            return self.reg_pat == other.reg_pat and self.shift_pat == other.shift_pat
        return False

    @_single_consumer
    def consume(self, op, ctx: ExecutionContext):
        if isinstance(op, arm_asm.ShiftedReg):
            self.reg_pat.consume([op.reg], ctx, _expect_done)
            if self.shift_pat is None:
                if op.shift is not None:
                    raise PatternValueMismatch(self, op)
            else:
                self.shift_pat.consume([op.shift], ctx, _expect_done)
        elif isinstance(op, arm_asm.Reg):
            if self.shift_pat is not None:
                self.shift_pat.consume([None], ctx, _expect_done)
            self.reg_pat.consume([op], ctx, _expect_done)
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
    def consume(self, op, ctx: ExecutionContext):
        if not isinstance(op, arm_asm.MemMulti):
            raise PatternTypeMismatch(self, op)
        _consume_list(self.reg_list, op.reg_list, ctx, _expect_done)


class RegRangePat:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        return f'RegRangePat({self.start!r}, {self.end!r})'

    def __str__(self):
        return f'{self.start}-{self.end}'

    def consume(self, operands: list, ctx: ExecutionContext, complete):
        try:
            s = operands[0]
        except IndexError:
            raise OperandsExhausted(self)

        if not isinstance(s, arm_asm.Reg):
            raise PatternTypeMismatch(self, s)

        self.start.consume([s], ctx, _expect_done)
        s_index = arm_asm.REG_INDEX[s.name]

        for i, o in enumerate(operands[1:]):
            if not isinstance(o, arm_asm.Reg):
                raise PatternTypeMismatch(self, o)
            if arm_asm.REG_INDEX[o.name] != s_index + i + 1:
                break
            try:
                with ctx.match_result.transact():
                    self.end.consume([o], ctx, _expect_done)
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

    def match(self, operands: list, ctx: ExecutionContext, **_kwargs):
        _consume_list(self.ops, operands, ctx, _expect_done)


class IntegerVal(ContainerBase):
    @_single_consumer
    def consume(self, op, _):
        if not isinstance(op, int):
            raise PatternTypeMismatch(self.value, op)
        if op != self.value:
            raise PatternValueMismatch(self.value, op)


class RegPat(ContainerBase):
    def consume(self, operands: list, ctx: ExecutionContext, complete):
        self.value.consume(operands, ctx, complete)


class Reg(ContainerBase):
    # noinspection PyUnusedLocal
    @_single_consumer
    def consume(self, op, _ctx: ExecutionContext):
        if not isinstance(op, arm_asm.Reg):
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

    def match(self, value, ctx: ExecutionContext, **_kwargs):
        ctx.match_result[self.capture] = value


class WildcardMulti(WildcardBase):
    symbol = '*'

    def consume(self, operands, ctx: ExecutionContext, complete):
        for i in range(len(operands) + 1):
            try:
                with ctx.match_result.transact():
                    complete(operands[i:])
                    ctx.match_result[self.capture] = operands[:i]
                    return
            except PatternMismatchException:
                continue
        raise NoMatches()


class WildcardOptional(WildcardBase):
    symbol = '?'

    def consume(self, operands: list, ctx: ExecutionContext, complete):
        match_result = ctx.match_result
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
    def consume(self, op, ctx: ExecutionContext):
        ctx.match_result[self.capture] = op


class ImmediatePat:
    def __init__(self, value):
        self.value = value

    @_single_consumer
    def consume(self, op, ctx: ExecutionContext):
        if not isinstance(op, arm_asm.Immediate):
            raise PatternTypeMismatch(self, op)

        self.value.consume([op.value], ctx, _expect_done)

    def __repr__(self):
        return f'ImmediatePat({self.value!r})'

    def __str__(self):
        return f'#{self.value}'

    def __eq__(self, other):
        if not isinstance(other, ImmediatePat):
            return False
        return self.value == other.value


class PureCodeLine(CodeLinePatternBase):
    @property
    def prefix(self):
        return '%'

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


class AddressPat(ContainerBase):
    def __init__(self, value):
        super().__init__(value)

    def match(self, ctx: ExecutionContext, **kwargs):
        self.value.match(ctx.cursor.address, ctx, **kwargs)
        ctx.fork_next_line().match(**kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        self.value.match_reverse(ctx.cursor.address, ctx, **kwargs)
        ctx.fork_next_line().match(**kwargs)

    @_single_consumer
    def consume(self, op, ctx: ExecutionContext):
        self.value.match(op, ctx)


class Address:
    def __init__(self, address):
        self.address = address

    def __repr__(self):
        return f'Address({self.address})'

    def __str__(self):
        return f'0x{self.address:X}'

    def match(self, address, _ctx: ExecutionContext, **_kwargs):
        if not isinstance(address, arm_asm.Address):
            return False
        if address.address != self.address:
            raise PatternValueMismatch(self.address, address)

    def __int__(self):
        return self.address


class Label(ContainerBase):
    def match(self, address, ctx: ExecutionContext, **_kwargs):
        ctx.match_result[self.value] = address


class BlockPat(BlockPattern):
    def __init__(self, lines, anchor_index=0):
        super().__init__(lines, anchor_index)

    def __repr__(self):
        if self.anchor_index == 0:
            return f'BlockPat({self.lines!r})'
        return f'BlockPat({self.lines!r}, {self.anchor_index})'

    def __str__(self):
        line_strs = []
        for i, line in enumerate(self.lines):
            prefix = '  > ' if i == self.anchor_index and i != 0 else '    '
            if isinstance(line, AddressPat):
                line_strs.append(f'{prefix}{line}:')
            elif isinstance(line, CommandPat):
                line_strs.append(indent(f'{prefix}{line!s}'))
            else:
                raise TypeError(f'Invalid line of type {type(line)}, {line}')

        return '\n'.join(line_strs)

    def __eq__(self, other):
        if not isinstance(other, BlockPat):
            return False
        return self.lines == other.lines and self.anchor_index == other.anchor_index


class InstructionPat(Matchable):
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

    def match_logic(self, ctx: ExecutionContext, **kwargs):
        inst = ctx.cursor.instruction
        if inst is None:
            raise PatternValueMismatch(self, ctx.cursor)
        self.opcode_pat.match(inst.opcode, ctx, **kwargs)
        self.operand_pats.match(inst.operands, ctx, **kwargs)

    def match(self, ctx: ExecutionContext, **kwargs):
        self.match_logic(ctx, **kwargs)
        next_ctx = ctx.fork_next_line().fork_next_instruction()
        next_ctx.match(**kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        ctx = ctx.fork_prev_instruction()
        self.match_logic(ctx, **kwargs)
        next_ctx = ctx.fork_next_line()
        next_ctx.match(**kwargs)


class PythonCodeBase(CodeLineBase, ABC):
    var_ix = 0

    def __init__(self, parts):
        self.parts = parts
        self._code, self._vars = self._gen_code()

    @property
    def code(self):
        return self._code

    @property
    def vars(self):
        return self._vars

    @classmethod
    def _gen_var(cls):
        ix = cls.var_ix + 1
        cls.var_ix = ix
        return f'var_{ix}'

    @staticmethod
    def _fix_indentation(code):
        lines = code.split('\n')
        stripped_lines = [line.lstrip() for line in lines]
        prefixes = [line[:-len(stripped)] for line, stripped in zip(lines, stripped_lines)]
        p = prefixes[0]
        assert all(px == ' ' * len(px) for px in prefixes)
        assert all(len(p) <= len(px) for px in prefixes[1:])
        lines = [line[len(p):] for line in lines]
        return '\n'.join(lines)

    def _gen_code(self):
        pieces = []
        ns = OrderedDict()
        for p in self.parts:
            if isinstance(p, str):
                pieces.append(p)
                continue
            assert isinstance(p, BlockPat), f'Parts: {self.parts}'
            var = self._gen_var()
            ns[var] = p
            pieces.append(var)
        code = ''.join(pieces)
        code = self._fix_indentation(code)
        return code, ns

    def __repr__(self):
        return f'{self.__class__.__name__}({self.parts!r})'

    def unquote(self):
        strs = []
        for p in self.parts:
            if isinstance(p, str):
                strs.append(p)
                continue
            assert isinstance(p, BlockPat)
            strs.append(f'${{{p!s}}}')
        return ''.join(strs)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.parts == other.parts


class PythonCodeLine(PythonCodeBase, CodeLinePatternBase):
    def __str__(self):
        return f'%{self.unquote()}'


class PythonCodeLines(PythonCodeBase, CodeLinePatternBase):
    def __str__(self):
        return f'%%\n{self.unquote()}\n%%'


class PythonMatchableGenerator(PythonCodeBase, CodeLineMatchableGenerator):
    pass


class PythonDataObj(PythonCodeBase):
    def __init__(self, code, obj_name=None):
        assert isinstance(code, str)
        super().__init__([code])
        self.obj_name = obj_name

    def __str__(self):
        if self.obj_name is None:
            return f".obj ${self.code}"
        else:
            return f".obj {self.obj_name}:{self.code}"

    def match_logic(self, obj_type, ctx: ExecutionContext):
        try:
            ctx.match_result[self.obj_name] = obj_type.parse_stream(ctx.cursor.create_data_stream())
        except ConstructError as e:
            raise ConstructParsingException(e)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        obj_type, _ = self.eval(ctx, **kwargs)
        obj_size = obj_type.sizeof()
        next_ctx = ctx.fork_next_line()
        next_ctx.cursor = ctx.cursor.get_cursor_by_offset(-obj_size)
        self.match_logic(obj_type, next_ctx)
        next_ctx.match(**kwargs)

    def match(self, ctx: ExecutionContext, **kwargs):
        obj_type, _ = self.eval(ctx, **kwargs)
        obj_size = obj_type.sizeof()
        self.match_logic(obj_type, ctx)
        next_ctx = ctx.fork_next_line()
        next_ctx.cursor = ctx.cursor.get_cursor_by_offset(obj_size)
        next_ctx.match(**kwargs)


class SizedData(ContainerBase):
    @property
    def size(self):
        raise NotImplementedError()

    @property
    def endian(self) -> Literal["little", "big"]:
        return 'little'

    def match_logic(self, ctx: ExecutionContext, **_kwargs):
        v = self.value
        data = int.from_bytes(ctx.cursor.read_bytes(self.size), self.endian)
        if isinstance(v, int):
            if data != v:
                raise PatternValueMismatch(data, v)
        else:
            assert isinstance(v, WildcardSingle)
            ctx.match_result[v.capture] = data

    def match(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        self.match_logic(ctx, **kwargs)
        return ctx.fork_offset(self.size)

    def match_reverse(self, ctx: ExecutionContext, **kwargs) -> ExecutionContext:
        ctx = ctx.fork_offset(-self.size)
        self.match_logic(ctx, **kwargs)
        return ctx


class DataByte(SizedData):
    @property
    def size(self):
        return 1


class DataWord(SizedData):
    @property
    def size(self):
        return 2


class DataDword(SizedData):
    @property
    def size(self):
        return 4


class DataQword(SizedData):
    @property
    def size(self):
        return 8


class DataSeq(ContainerBase):
    def match(self, ctx: ExecutionContext, **kwargs):
        seq = self.value  # type: List[SizedData]
        for p in seq:
            ctx = p.match(ctx, **kwargs)
        ctx.fork_next_line().match(**kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        seq = self.value  # type: List[SizedData]
        for p in reversed(seq):
            ctx = p.match_reverse(ctx, **kwargs)
        ctx.fork_next_line().match(**kwargs)


def data_pat_array(data_type):
    return lambda data_seq: DataSeq([data_type(p) for p in data_seq])


byte_pat_array = data_pat_array(DataByte)
word_pat_array = data_pat_array(DataWord)
dword_pat_array = data_pat_array(DataDword)
qword_pat_array = data_pat_array(DataQword)


def basic_array_type(array_type):
    # noinspection PyUnusedLocal
    def func(self, parts):
        (pats,) = parts
        return array_type(pats)

    return func


class AnchoredLine:
    def __init__(self, line):
        self.line = line


class ExactSkipPat:
    def __init__(self, skip_count):
        self.skip_count = skip_count

    def match_logic(self, advance, ctx: ExecutionContext, **kwargs):
        next_ctx = ctx.fork_next_line()
        for i in range(self.skip_count):
            next_ctx = advance(next_ctx)
        next_ctx.match(**kwargs)

    def match(self, ctx: ExecutionContext, **kwargs):
        return self.match_logic(lambda x: x.fork_next_instruction(), ctx, **kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        return self.match_logic(lambda x: x.fork_prev_instruction(), ctx, **kwargs)


class SkipPat:
    def __init__(self, min_skip=None, max_skip=None):
        self.min_skip = min_skip
        self.max_skip = max_skip

    @classmethod
    def create(cls, min_skip, max_skip):
        if min_skip is not None and max_skip is not None and min_skip == max_skip:
            return ExactSkipPat(min_skip)
        return cls(min_skip, max_skip)

    def match_logic(self, advance, ctx: ExecutionContext, **kwargs):
        mr = ctx.match_result
        next_ctx = ctx.fork_next_line()
        skip_ix = 0
        while True:
            if self.max_skip is not None and skip_ix > self.max_skip:
                raise PatternValueMismatch(self, ctx.cursor)

            if self.min_skip is None or skip_ix >= self.min_skip:
                try:
                    with mr.transact():
                        next_ctx.match(**kwargs)
                    return
                except PatternMismatchException:
                    pass

            skip_ix += 1
            next_ctx = advance(next_ctx)

    def match(self, ctx: ExecutionContext, **kwargs):
        return self.match_logic(lambda x: x.fork_next_instruction(), ctx, **kwargs)

    def match_reverse(self, ctx: ExecutionContext, **kwargs):
        return self.match_logic(lambda x: x.fork_prev_instruction(), ctx, **kwargs)

    def __str__(self):
        a = ['', '']
        if self.min_skip is not None:
            a[0] = str(self.min_skip)
        if self.max_skip is not None:
            a[1] = str(self.max_skip)

        if any(a):
            rng = ' {{{}}}'.format(', '.join(a))
        else:
            rng = ''

        return f'SkipPat[...{rng}]'


# noinspection PyMethodMayBeStatic
class ArmPatternTransformer(Transformer):
    def skip_exact(self, parts):
        (count, ) = parts
        assert isinstance(count, Token)
        val = int(count.value, 0)
        return ExactSkipPat(val)

    def skip_range(self, parts):
        start, end = map(lambda x: int(x.value, 0) if x is not None else None, parts)
        return SkipPat.create(start, end)

    def identifier(self, parts):
        (name, ) = parts
        assert isinstance(name, Token)
        return name.value

    def matchable_code(self, parts):
        (code_parts, ) = parts
        return CommandPat(PythonMatchableGenerator(code_parts))

    def opcode_wildcard(self, parts):
        (capture,) = parts
        return OpcodePat('*', capture)

    def data_val_pat(self, parts):
        (val, ) = parts
        if isinstance(val, Token):
            return int(val, 0)
        assert isinstance(val, WildcardSingle)
        return val

    def data_val_pats(self, parts):
        return parts

    db = basic_array_type(byte_pat_array)
    dw = basic_array_type(word_pat_array)
    dd = basic_array_type(dword_pat_array)
    dq = basic_array_type(qword_pat_array)

    def data_obj_type(self, parts):
        (code, ) = parts
        return code

    def data_obj(self, parts):
        (obj, ) = parts
        assert isinstance(obj, PythonDataObj)
        return obj

    def anonymous_data_obj(self, parts):
        (code, ) = parts
        assert isinstance(code, str)
        return PythonDataObj(code)

    def named_data_obj(self, parts):
        name, code = parts
        assert isinstance(code, str)
        assert isinstance(name, str)
        return PythonDataObj(code, name)

    def data_line(self, parts):
        (pat, ) = parts
        return pat

    def skip_line(self, parts):
        (pat, ) = parts
        return pat

    def _opcode_pat(self, parts):
        pat, capture = parts
        assert isinstance(pat, Token)
        return OpcodePat(pat.value, capture)

    approx_mov = _opcode_pat
    approx_arithmetic = _opcode_pat
    approx_bitwise = _opcode_pat
    approx_compare = _opcode_pat
    approx_branch_rel = _opcode_pat
    approx_branch_ind = _opcode_pat
    approx_multiply = _opcode_pat
    approx_shift = _opcode_pat
    approx_shift_unary = _opcode_pat
    approx_stack_mem_multi = _opcode_pat

    def _exact_opcode(self, parts):
        (pat,) = parts
        assert isinstance(pat, Token)
        return OpcodePat(pat.value)

    exact_mov = _exact_opcode
    exact_arithmetic = _exact_opcode
    exact_bitwise = _exact_opcode
    exact_compare = _exact_opcode
    exact_branch_rel = _exact_opcode
    exact_branch_ind = _exact_opcode
    exact_multiply = _exact_opcode
    exact_shift = _exact_opcode
    exact_shift_unary = _exact_opcode
    exact_stack_mem_multi = _exact_opcode

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

    def anchored_line_pat(self, parts):
        (line_pat, ) = parts
        return AnchoredLine(line_pat)

    def python_code_line(self, parts):
        result = []
        for part in parts:
            if isinstance(part, Token):
                result.append(part.value)
                continue
            assert isinstance(part, str)
            result.append(part)
        return ''.join(result)

    def python_code_lines(self, lines):
        for line in lines:
            assert isinstance(line, str)
        return lines

    def code_line(self, parts):
        (code, ) = parts
        assert isinstance(code, str)
        return CommandPat(PythonCodeLine([code]))

    def code_lines(self, parts):
        (code_parts, ) = parts
        return CommandPat(PythonCodeLines(code_parts))

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
    bitwise_operands_pat = operands_pat
    compare_operands_pat = operands_pat
    branch_rel_operands_pat = operands_pat
    branch_ind_operands_pat = operands_pat
    multiply_operands_pat = operands_pat
    shift_operands_pat = operands_pat
    shift_pat_operands_pat = operands_pat
    shift_unary_operands_pat = operands_pat
    stack_mem_multi_operands_pat = operands_pat

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

    def simple_block_pat(self, line_pats):
        lines = []
        for lp in line_pats:
            assert isinstance(lp, list), lp
            lines.extend(lp)
        return BlockPat(lines)

    def anchored_block_pat(self, line_pats):
        lines = []
        anchor_ix = None
        for i, lp in enumerate(line_pats):
            if isinstance(lp, AnchoredLine):
                assert anchor_ix is None
                anchor_ix = i
                lp = lp.line
            assert isinstance(lp, list), lp
            lines.extend(lp)
        assert anchor_ix is not None
        return BlockPat(lines, anchor_index=anchor_ix)

    def flexible_operand_pat(self, parts):
        (pat, ) = parts
        return pat

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
