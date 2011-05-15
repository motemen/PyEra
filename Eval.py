import re

class EvalException:
    def __init__ (self, msg):
        self.msg = msg

    def __repr__ (self):
        return self.msg

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
        ':*': '_eval_value_subscription',
    }

    def __init__ (self, env):
        self.env = env

    def eval_lvalue (self, value):
        (name, subs) = (value[0], value[1]) # ex. ( 'TALENT', [ 'ASSI', '83' ] )
        dic = self.env['variable']
        for s in subs:
            (dic, name) = (dic.setdefault(name, {}), self.eval_expr(s))
        return (dic, name)

    def eval_atom (self, atom):
        if re.match('^-?\d+$', atom):
            return int(atom)
        else:
            return self.env['variable'].setdefault(atom, 0) # TODO default value

    def _eval_value_subscription (self, args):
        (dic, name) = self.eval_lvalue([ args[0], args[1:] ])
        return dic.setdefault(name, 0) # TODO default value

    def eval_op (self, op, args):
        bin_op = self.OP_BINARY_IMPL[op]
        if isinstance(bin_op, str):
            return getattr(self, bin_op)(args)
        else:
            return bin_op(self.eval_expr(args[0]), self.eval_expr(args[1]))

    def eval_expr (self, expr):
        if isinstance(expr, dict):
            return self.eval_op(expr['operator'], expr['operand'])
        else:
            return self.eval_atom(expr)

    def eval_statement (self, stmt):
        if stmt['type'] == 'LET':
            # TODO op
            (dic, name) = self.eval_lvalue(stmt['lhs'])
            dic[name] = self.eval_expr(stmt['rhs'])

        elif stmt['type'] == 'IF':
            for (cond, block) in stmt['cond']:
                if self.eval_expr(cond):
                    self.eval_block(block)
                    break
            else:
                self.eval_block(stmt['else'])

        elif stmt['type'] == 'REPEAT':
            count = self.eval_expr(stmt['count'])
            for i in range(count):
                self.env['variable']['COUNT'] = i
                self.eval_block(stmt['block'])

        else:
            print 'Could not handle stmt: %s' % stmt

    def eval_block (self, block):
        for s in block:
            self.eval_statement(s)
