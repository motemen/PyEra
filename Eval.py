import re

class Eval:
    OP_BINARY_IMPL = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y,
        '>': lambda x, y: x > y,
        '<': lambda x, y: x < y,
        '>=': lambda x, y: x >= y,
        '<=': lambda x, y: x <= y,
        '==': lambda x, y: x == y,
        '!=': lambda x, y: x != y,
        '||': lambda x, y: x or y,
        '&&': lambda x, y: x and y,
    }

    def __init__ (self, env):
        self.env = env

    # XXX
    def eval_atom (self, atom):
        if re.match('^-?\d+$', atom):
            return int(atom)
        else:
            return self.env['variable'][atom]

    def eval_op (self, op, args):
        bin_op = self.OP_BINARY_IMPL[op]
        if bin_op:
            return bin_op(self.eval_expr(args[0]), self.eval_expr(args[1]))

    def eval_expr (self, expr):
        if isinstance(expr, dict):
            return self.eval_op(expr['operator'], expr['operand'])
        else:
            return self.eval_atom(expr)

    def eval_statement (self, stmt):
        if stmt['type'] == 'LET':
            # TODO op
            # TODO index
            self.env['variable'][stmt['lhs']] = self.eval_expr(stmt['rhs'])
        elif stmt['type'] == 'REPEAT':
            count = int(self.eval_expr(stmt['count'][0]))
            for i in range(count):
                self.env['variable']['COUNT'] = i
                self.eval_block(stmt['block'])


    def eval_block (self, block):
        print 'eval_block', block
        for s in block:
            self.eval_statement(s)
