from enum import Enum
from lark import Transformer


REGS = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12', 'sp', 'lr', 'pc')


def _build_reg_index():
    result = {}
    for i, r in enumerate(REGS):
        result[r.upper()] = i
        result[r.lower()] = i
    return result


REG_INDEX = _build_reg_index()


class Fixity(Enum):
    IMMEDIATE = 0
    PREFIX = 1
    POSTFIX = 2


class Line:
    def __init__(self, instruction, address=None):
        self.address = address
        self.instruction = instruction

    def __str__(self):
        address_str = ''
        if self.address is not None:
            address_str = '{}: '.format(self.address)
        return address_str + str(self.instruction)


class ShiftedReg:
    def __init__(self, reg, shift):
        self.reg = reg
        self.shift = shift

    def __str__(self):
        if self.shift is None:
            return self.reg
        else:
            return '{}, {}'.format(self.reg, self.shift)


class Instruction:
    def __init__(self, opcode, operands):
        self.opcode = opcode
        self.operands = operands

    def __str__(self):
        ps = ', '.join([str(o) for o in self.operands])
        return ' '.join([self.opcode, ps])


class Operands:
    def __init__(self, *ops):
        self.ops = ops

    def __str__(self):
        return ', '.join([str(o) for o in self.ops])


class Immediate:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '#{}'.format(self.value)


class RegList:
    def __init__(self, regs):
        self.regs = regs

    def __str__(self):
        ps = []

        range_len = 1
        range_prev = REG_INDEX[self.regs[0]]

        def _handle_complete_range():
            if range_len == 0:
                pass
            if range_len == 1:
                ps.append(REGS[range_prev])
            elif range_len == 2:
                ps.append(REGS[range_prev - 1])
                ps.append(REGS[range_prev])
            else:
                ps.append('{}-{}'.format(REGS[range_prev - range_len + 1], REGS[range_prev]))

        for r in self.regs[1:]:
            current_index = REG_INDEX[r]
            if current_index - 1 == range_prev:
                range_len += 1
            else:
                _handle_complete_range()
                range_len = 1
            range_prev = current_index

        _handle_complete_range()
        return ', '.join(ps)


class MemMulti:
    def __init__(self, reg_list):
        self.reg_list = reg_list

    def __str__(self):
        return '{{{}}}'.format(self.reg_list)


class MemAccess:
    def __init__(self, reg, offset: Immediate, fixity: Fixity):
        if offset is None:
            assert fixity == Fixity.IMMEDIATE
            offset = Immediate(0)

        self.reg = reg
        self.offset = offset
        self.fixity = fixity

    def __str__(self):
        if self.fixity == Fixity.IMMEDIATE:
            return '[{}, {}]'.format(self.reg, self.offset)
        if self.fixity == Fixity.PREFIX:
            return '[{}, {}]!'.format(self.reg, self.offset)
        if self.fixity == Fixity.POSTFIX:
            return '[{}], {}'.format(self.reg, self.offset)

        raise ValueError('Invalid fixity: {}'.format(self.fixity))


class ArmTransformer(Transformer):
    def line(self, parts):
        address, instruction = parts
        return Line(instruction, address)

    def instruction(self, inst):
        opcode = inst[0]
        operands = inst[1:]
        return Instruction(opcode, operands)

    def arithmetic_operands(self, operands):
        op_cnt = len(operands)
        assert op_cnt in (2, 3)
        if op_cnt == 2:
            rd, rm_shift = operands
            return Operands(rd, rd, rm_shift)
        else:
            rd, rn, rm_shift = operands
            return Operands(rd, rn, rm_shift)

    def mem_single_operand(self, operands):
        return operands  # TODO: Fix

    def shifted_reg(self, parts):
        reg, shift = parts
        return ShiftedReg(reg, shift)

    def mov_operands(self, parts):
        rd, op2 = parts
        return Operands(rd, op2)

    def immediate(self, value):
        assert len(value) == 1
        return Immediate(int(value[0], 0))

    def mem_expr_immediate(self, parts):
        dst, src, offset = parts
        return Operands(dst, MemAccess(src, offset, Fixity.IMMEDIATE))

    def mem_expr_pre_indexed(self, parts):
        dst, src, offset = parts
        return Operands(dst, MemAccess(src, offset, Fixity.PREFIX))

    def mem_expr_post_index(self, parts):
        dst, src, offset = parts
        return Operands(dst, MemAccess(src, offset, Fixity.POSTFIX))

    def reg_range(self, parts):
        start_reg, end_reg = parts
        start_ix = REG_INDEX[start_reg]
        end_ix = REG_INDEX[end_reg]
        assert start_ix < end_ix

        result = []
        for i in range(start_ix, end_ix + 1):
            result.append(REGS[i])
        return result

    def reg_list(self, parts):
        result = []
        for p in parts:
            if isinstance(p, str):
                if p in result:
                    raise ValueError('Register {} already in list!'.format(p))
                result.append(p)
            elif isinstance(p, list):
                for e in p:
                    if not isinstance(e, str):
                        raise TypeError('Got {} of type {}, expected str', e, type(e))
                    if e in result:
                        raise ValueError('Register {} already in list!'.format(e))
                    result.append(e)
            else:
                raise TypeError('Got {} of type {}, expected str or list[str]'.format(p, type(p)))
        return RegList(result)

    def mem_multi_operand(self, parts):
        dst, reg_list = parts
        return Operands(dst, MemMulti(reg_list))
