import re
# vim: set fileencoding=utf8:

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

    def __init__ (self, parser):
        self.env = {
            'variables': {},
            'functions': parser.functions,
        }
        self.predefined_function = PredefinedFunction(self)
        self.stack = []

    def eval_lvalue (self, value):
        (name, subs) = (value[0], value[1]) # ex. ( 'TALENT', [ 'ASSI', '83' ] )
        dic = self.env['variables']
        for s in subs:
            (dic, name) = (dic.setdefault(name, {}), self.eval_expr(s))
        return (dic, name)

    def eval_atom (self, atom):
        if re.match('^-?\d+$', atom):
            return int(atom)
        else:
            return int(self.env['variables'].setdefault(atom, 0)) # TODO default value

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
        print 'eval_statement', stmt
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
                self.env['variables']['COUNT'] = i
                self.eval_block(stmt['block'])

        elif stmt['type'] == 'FUNC_CALL':
            predefined = getattr(self.predefined_function, stmt['funcname'], None)
            if predefined:
                predefined(stmt['args'])
            else:
                self.predefined_function.CALL(stmt['funcname'])

        elif stmt['type'] == 'LABEL':
            self.current_frame().labels[stmt['name']] = self.current_frame().next_index

        else:
            print 'Could not handle stmt: %s' % stmt

    def current_frame (self):
        return self.stack[-1]

    def eval_block (self, block):
        frame = Frame(block)
        self.stack.append(frame)

        while self.eval_next_statement():
            pass

        if self.current_frame() == frame:
            self.stack.pop()

    def eval_next_statement (self):
        if self.current_frame().at_last():
            return False

        statement = self.current_frame().next_statement()
        self.current_frame().step()
        self.eval_statement(statement)

        return True

class PredefinedFunction:
    def __init__ (self, e):
        self.eval = e

    def CALL (self, name):
        print 'CALL %s' % name
        func = self.eval.env['functions'].get(name)
        if func is None:
            raise EvalException('Function does not exist: \'%s\'' % name)
        self.eval.eval_block(func['body']) # TODO args
        print 'END %s' % name

    def DRAWLINE (self, args):
        print '----------'

    def PRINTL (self, args):
        print args

    def PRINTFORMW (self, args):
        print 'stub PRINT_SHOPITEM'
        print args

    def PRINT_SHOPITEM (self, args):
        print 'stub PRINT_SHOPITEM'

    def INPUT (self, args):
        self.eval.env['variables']['RESULT'] = raw_input()

    def GOTO (self, label):
        while True:
            index = self.eval.current_frame().labels.get(label)
            if index is None:
                self.eval.stack.pop()
                continue
            self.eval.current_frame().next_index = index
            break
        else:
            raise EvalException('Could not find label \'%s\'' % label)

class Frame:
    def __init__ (self, block):
        self.block = block
        self.next_index = 0
        self.labels = {}

    def at_last (self):
        return self.next_index >= len(self.block)

    def next_statement (self):
        return self.block[self.next_index]

    def step (self):
        self.next_index += 1
