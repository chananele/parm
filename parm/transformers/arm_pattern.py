from lark import Transformer

from parm.transformers import arm


class LinePat:
    def __init__(self, instruction_pat, address_pat=None):
        self.instruction_pat = instruction_pat
        self.address_pat = address_pat

    def __str__(self):
        address_str = ''
        if self.address_pat is not None:
            address_str = '{}: '.format(self.address_pat)
        return address_str + str(self.instruction_pat)


class InstructionPat:
    def __init__(self, opcode_pat, operand_pats):
        self.opcode_pat = opcode_pat
        self.operand_pats = operand_pats

    def __str__(self):
        ps = ', '.join([str(o) for o in self.operand_pats])
        return ' '.join([self.opcode_pat, ps])


class ArmPatternTransformer(Transformer):
    def line_pat(self, parts):
        address_pat, instruction_pat = parts
        return LinePat(instruction_pat, address_pat)

    def instruction_pat(self, inst):
        opcode = inst[0]
        operands = inst[1:]
        return InstructionPat(opcode, operands)
