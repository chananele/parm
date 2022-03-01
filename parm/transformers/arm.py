from lark import Transformer, Token


REGS = ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12', 'sp', 'lr', 'pc')


def _build_reg_index():
    result = {}
    for i, r in enumerate(REGS):
        result[r.upper()] = i
        result[r.lower()] = i
    return result


REG_INDEX = _build_reg_index()


class Line:
    def __init__(self, instruction, address=None):
        self.address = address
        self.instruction = instruction

    def __eq__(self, other):
        if not isinstance(other, Line):
            return False
        if self.address != other.address:
            return False
        return self.instruction == other.instruction

    def __repr__(self):
        if self.address is None:
            return f'Line({self.instruction!r})'
        else:
            return f'Line({self.instruction!r}, {self.address!r})'

    def __str__(self):
        address_str = ''
        if self.address is not None:
            address_str = '{}: '.format(self.address)
        return address_str + str(self.instruction)


class Reg:
    def __init__(self, name):
        assert isinstance(name, str)
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, Reg):
            return False
        return self.name == other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'Reg({self.name!r})'


class ShiftedReg:
    def __init__(self, reg, shift=None):
        self.reg = reg
        self.shift = shift

    def __eq__(self, other):
        if not isinstance(other, ShiftedReg):
            return False
        return other.reg == self.reg and other.shift == self.shift

    def __repr__(self):
        if self.shift is None:
            return f'ShiftedReg({self.reg!r})'
        else:
            return f'ShiftedReg({self.reg!r}, {self.shift!r})'

    def __str__(self):
        if self.shift is None:
            return self.reg.name
        else:
            return '{}, {}'.format(self.reg, self.shift)


class Instruction:
    def __init__(self, opcode, operands):
        self.opcode = opcode
        self.operands = operands

    def __eq__(self, other):
        if not isinstance(other, Instruction):
            return False
        if not self.opcode == other.opcode:
            return False
        if not self.operands == other.operands:
            return False
        return True

    def __repr__(self):
        return f'Instruction({self.opcode!r}, {self.operands!r})'

    def __str__(self):
        ps = ', '.join([str(o) for o in self.operands])
        return ' '.join([self.opcode, ps])


class Operands:
    def __init__(self, *ops):
        self.ops = ops

    def __iter__(self):
        return iter(self.ops)

    def __eq__(self, other):
        if not isinstance(other, Operands):
            return False
        return self.ops == other.ops

    def __repr__(self):
        return f'Operands({", ".join(repr(o) for o in self.ops)})'

    def __str__(self):
        return ', '.join([str(o) for o in self.ops])


class Address:
    def __init__(self, address):
        self.address = address

    def __eq__(self, other):
        if not isinstance(other, Address):
            return False
        return self.address == other.address

    def __str__(self):
        return f'0x{self.address:X}'

    def __repr__(self):
        return f'Address(0x{self.address:X})'


class Immediate:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, Immediate):
            return False
        return self.value == other.value

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return '#{}'.format(self.value)


class RegList:
    def __init__(self, regs):
        self.regs = regs  # type: list[Reg]

    def __repr__(self):
        return f'RegList({self.regs!r})'

    def __eq__(self, other):
        if not isinstance(other, RegList):
            return False
        return self.regs == other.regs

    def __str__(self):
        ps = []

        range_len = 1
        range_prev = REG_INDEX[self.regs[0].name]

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
            current_index = REG_INDEX[r.name]
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

    def __eq__(self, other):
        if not isinstance(other, MemMulti):
            return False
        return self.reg_list == other.reg_list

    def __repr__(self):
        return f'MemMulti({self.reg_list!r})'

    def __str__(self):
        return '{{{}}}'.format(self.reg_list)


class MemAccess:
    def __init__(self, reg, offset):
        self.reg = reg
        self.offset = offset

    def __eq__(self, other):
        if type(other) is not type(self):
            return False
        return self.reg == other.reg and self.offset == other.offset


class MemAccessOffset(MemAccess):
    def __str__(self):
        return f'[{self.reg}, {self.offset}]'

    def __repr__(self):
        return f'MemAccessOffset({self.reg!r}, {self.offset!r})'


class MemAccessPreIndexed(MemAccess):
    def __str__(self):
        return f'[{self.reg}, {self.offset}]!'

    def __repr__(self):
        return f'MemAccessPreIndexed({self.reg!r}, {self.offset!r})'


class MemAccessPostIndexed(MemAccess):
    def __str__(self):
        return f'[{self.reg}], {self.offset}'

    def __repr__(self):
        return f'MemAccessPostIndexed({self.reg!r}, {self.offset!r})'


class ArmTransformer(Transformer):
    def line(self, parts):
        address, instruction = parts
        return Line(instruction, address)

    def instruction(self, inst):
        opcode = inst[0]
        operands = inst[1:]
        assert isinstance(opcode, Token)
        return Instruction(opcode.value, operands)

    def arithmetic_operands(self, operands):
        op_cnt = len(operands)
        assert op_cnt in (2, 3)
        if op_cnt == 2:
            rd, rm_shift = operands
            assert isinstance(rd, Reg)
            return Operands(rd, rd, rm_shift)
        else:
            rd, rn, rm_shift = operands
            assert isinstance(rd, Reg)
            assert isinstance(rn, Reg)
            return Operands(rd, rn, rm_shift)

    def mem_single_operand(self, operands):
        return operands

    def reg(self, parts):
        (name, ) = parts
        assert isinstance(name, Token)
        return Reg(name.value)

    def shifted_reg(self, parts):
        reg, shift = parts
        assert isinstance(reg, Reg)
        if shift is None:
            return ShiftedReg(reg)
        assert isinstance(shift, Token)
        return ShiftedReg(reg, shift.value)

    def mov_operands(self, parts):
        rd, op2 = parts
        return Operands(rd, op2)

    def immediate(self, value):
        assert len(value) == 1
        return Immediate(int(value[0], 0))

    def mem_expr_immediate(self, parts):
        dst, src, offset = parts
        if offset is None:
            offset = Immediate(0)
        return Operands(dst, MemAccessOffset(src, offset))

    def mem_expr_immediate_pre(self, parts):
        dst, src, offset = parts
        return Operands(dst, MemAccessPreIndexed(src, offset))

    def mem_expr_immediate_post(self, parts):
        dst, src, offset = parts
        return Operands(dst, MemAccessPostIndexed(src, offset))

    mem_expr_reg = mem_expr_immediate
    mem_expr_reg_pre = mem_expr_immediate_pre
    mem_expr_reg_post = mem_expr_immediate_post

    def reg_range(self, parts):
        start_reg, end_reg = parts
        assert isinstance(start_reg, Reg)
        assert isinstance(end_reg, Reg)

        start_ix = REG_INDEX[start_reg.name]
        end_ix = REG_INDEX[end_reg.name]
        assert start_ix < end_ix

        result = []
        for i in range(start_ix, end_ix + 1):
            result.append(Reg(REGS[i]))
        return result

    def reg_list(self, parts):
        result = []
        for p in parts:
            if isinstance(p, Reg):
                if p in result:
                    raise ValueError('Register {} already in list!'.format(p))
                result.append(p)
            elif isinstance(p, list):
                for e in p:
                    if not isinstance(e, Reg):
                        raise TypeError('Got {} of type {}, expected Reg', e, type(e))
                    if e in result:
                        raise ValueError('Register {} already in list!'.format(e))
                    result.append(e)
            else:
                raise TypeError('Got {} of type {}, expected Reg or list[Reg]'.format(p, type(p)))
        return RegList(result)

    def mem_multi_operand(self, parts):
        dst, reg_list = parts
        return Operands(dst, MemMulti(reg_list))

    def address(self, parts):
        (num, ) = parts
        assert isinstance(num, Token)
        return Address(int(num.value, 0))
