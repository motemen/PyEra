#!/usr/bin/env python
# vim: set fileencoding=utf8:

import re

class ParseException:
    def __init__ (self, msg):
        self.msg = msg

    def __repr__ (self):
        return self.msg

class Parser:
    FUNCNAME = r'\w+'
    LITERAL  = r'-?\d+'
    VARNAME  = r'\w+'
    OPLET    = r'[+-/*|]?='

    RE_FUNC_DECL   = re.compile(r'^@(?P<funcname>%s)$' % FUNCNAME)
    RE_FUNC_PROP   = re.compile(r'^#(?P<prop>\w+)$')
    RE_LET         = re.compile(r'^(?P<lhs>%s)\s*(?P<op>%s)\s*(?P<rhs>.+)$' % ( '.+?', OPLET )) # TODO lhs
    RE_FUNC_CALL   = re.compile(r'^(?P<funcname>%s)\s*(?P<args>.*)$' % FUNCNAME)
    RE_LABEL       = re.compile(r'^\$(?P<name>\w+)')

    RE_STMT_IF     = re.compile(r'^IF\s+(?P<expr>.+)$')
    RE_STMT_ELSE   = re.compile(r'^ELSE\b')
    RE_STMT_ELSEIF = re.compile(r'^ELSEIF\s+(?P<expr>.+)$')
    RE_STMT_ENDIF  = re.compile(r'^ENDIF\b')
    RE_STMT_SIF    = re.compile(r'^SIF\s+(?P<expr>.+)$')
    RE_STMT_REPEAT = re.compile(r'^REPEAT\s+(?P<expr>.+)$')
    RE_STMT_REND   = re.compile(r'^REND$')

    RE_STMT_CONTINUE = re.compile(r'^CONTINUE$')

    # expr
    RE_VALUE       = re.compile(r'^(?:%s|%s)' % ( LITERAL, VARNAME ))

    OP = [
        [ '||' ],
        [ '&&' ],
        [ '|' ],
        [ '&' ],
        [ '<', '<=', '>', '>=', '==', '!=' ],
        [ '+', '-' ],
        [ '*', '/', '%' ],
        # ':' については左結合でないと困るので特殊処理が入って
        # ':*' というオペレータに変換される
        [ ':' ],
    ]

    RE_OP = [
        re.compile(r'\|\|'),
        re.compile(r'&&'),
        re.compile(r'\|\s+'),
        re.compile(r'&\s+'),
        re.compile(r'<=?|>=?|==|!='),
        re.compile(r'\+|-'),
        re.compile(r'\*|/|%'),
        re.compile(r':')
    ]

    CONSUME_RULES = [
        ( RE_FUNC_DECL,   'consume_func_decl' ),
        ( RE_FUNC_PROP,   'consume_func_prop' ),

        ( RE_STMT_IF,     'consume_stmt_if' ),
        ( RE_STMT_ELSEIF, 'consume_stmt_elseif' ),
        ( RE_STMT_ELSE,   'consume_stmt_else' ),
        ( RE_STMT_ENDIF,  'consume_stmt_endif' ),
        ( RE_STMT_SIF,    'consume_stmt_sif' ),

        ( RE_STMT_REPEAT, 'consume_stmt_repeat' ),
        ( RE_STMT_REND,   'consume_stmt_rend' ),

        ( RE_STMT_CONTINUE, 'consume_stmt_continue' ),

        ( RE_LABEL,       'consume_label' ),

        ( RE_LET,         'consume_let' ),

        ( RE_FUNC_CALL,   'consume_func_call' ),
    ]

    def __init__ (self):
        self.functions = {}
        self.stack = []

    def push (self, code):
        self.stack.append(code)

    def pop (self):
        self.stack.pop()

    def next (self, n):
        self.stack[-1](n)

    def clear (self):
        self.stack = []

    def parse (self, source):
        lines = source.split("\n")
        for line in lines:
            self.parse_line(line)

    def parse_line (self, line):
        import re # ???
        line = line.rstrip("\n\r")
        line = re.sub(r';.*$', '', line)
        line = re.sub(r'^\s+', '', line)

        if len(line) == 0:
            return

        for (re, c) in self.CONSUME_RULES:
            m = re.match(line)
            if m:
                getattr(self, c)(m.groupdict())
                break
        else:
            print 'Could not parse: [%s]' % line

    # value ::= varname | value ':' varname | value ':' '(' expr ')'
    def parse_value (self, value):
        parts = re.split(r':', value)
        return [ parts[0], [ self.parse_expr(p) for p in parts[1:] ] ]

    def parse_expr (self, expr):
        (token, rest) = self._parse_expr(expr)
        if len(rest) > 0:
            raise ParseException('Parsing %s remaining %s' % (expr, rest))
        return token

    def _parse_atom_value (self, expr):
        m = self.RE_VALUE.match(expr)
        if m == None:
            raise ParseException('Expected literal: %s' % expr)
        token = m.group()
        return (token, expr[m.end():])

    def _parse_expr (self, string, depth = 0):
        string = re.sub(r'^\s*', '', string)

        # '(' expr ')'
        if re.match(r'^\(', string):
            (token, string) = self._parse_expr(string[1:])

        # atom_value ::= varname | literal
        elif depth >= len(self.OP):
            m = self.RE_VALUE.match(string)
            if m == None:
                raise ParseException('Expected literal: %s' % string)
            token = m.group()
            return (token, string[m.end():])

        # term     ::= factor '*' term
        # expr_{n} ::= expr_{n+1} {op} expr_{n}
        else:
            (token, string) = self._parse_expr(string, depth + 1)
            string = re.sub('^\s*', '', string)

        while True:
            m = self.RE_OP[depth].match(string)
            if m == None:
                if re.match(r'^\)', string):
                    string = string[1:]
                return (token, string)
            op = m.group()
            string = string[m.end():]
            (token2, string) = self._parse_expr(string, depth + 1)
            token = { 'operator': op, 'operand': [ token, token2 ] }

    # { ':', [ A, { ':', [ B, C ] } ] } -> [ A, B, C ]
    def _expand_op_colon (self, node):
        if not isinstance(node, dict):
            return [ node ]

        if node['operator'] == ':*':
            return node['operand']

        if node['operator'] != ':':
            return [ node ]

        (left, right) = node['operand'][0:2]
        return [ left ] + self._expand_op_colon(right)

    def consume_func_decl (self, args):
        node = { 'type': 'FUNCTION', 'body': [] }
        self.clear()
        # TODO function vs event
        # self.functions[ args['funcname'] ] = node
        self.functions.setdefault(args['funcname'], []).append(node)
        def _ (n):
            if n['type'] == 'FUNC_PROP':
                node['prop'] = n['prop']
            else:
                node['body'].append(n)
        self.push(_)

    def consume_func_prop (self, args):
        node = { 'type': 'FUNC_PROP', 'prop': args['prop'] }
        self.next(node)

    def consume_let (self, args):
        rhs = self.parse_expr(args['rhs'])
        m = re.match(r'^(.)=$', args['op'])
        if m:
            rhs = { 'operator': m.group(1), 'operand': [ self.parse_expr(args['lhs']), rhs ] }
        node = { 'type': 'LET', 'lhs': self.parse_value(args['lhs']), 'op': '=', 'rhs': rhs }
        self.next(node)

    def consume_func_call (self, args):
        node = { 'type': 'FUNC_CALL', 'funcname': args['funcname'], 'args': args['args'] }
        self.next(node)

    def consume_stmt_if (self, args):
        node = { 'type': 'IF', 'cond': [ ( self.parse_expr(args['expr']), [] ) ], 'else': [] }
        self.next(node)
        def _ (n):
            if n['type'] == 'ELSEIF':
                node['cond'].append((n['expr'], []))
            elif n['type'] == 'ELSE':
                def _ (n):
                    if n['type'] == 'ENDIF':
                        self.pop()
                    else:
                        node['else'].append(n)
                self.pop()
                self.push(_)
            elif n['type'] == 'ENDIF':
                self.pop()
            else:
                node['cond'][-1][1].append(n)
        self.push(_)

    def consume_stmt_elseif (self, args):
        node = { 'type': 'ELSEIF', 'expr': self.parse_expr(args['expr']) }
        self.next(node)

    def consume_stmt_else (self, args):
        node = { 'type': 'ELSE' }
        self.next(node)

    def consume_stmt_endif (self, args):
        node = { 'type': 'ENDIF' }
        self.next(node)

    def consume_stmt_sif (self, args):
        node = { 'type': 'IF', 'cond': [ ( self.parse_expr(args['expr']), [] ) ], 'else': [] }
        self.next(node)
        def _ (n):
            node['cond'][-1][1].append(n)
            self.pop()
        self.push(_)

    def consume_stmt_repeat (self, args):
        node = { 'type': 'REPEAT', 'count': self.parse_expr(args['expr']), 'block': [] }
        self.next(node)
        self.push(lambda n: node['block'].append(n))

    def consume_stmt_rend (self, args):
        self.pop()

    def consume_stmt_continue (self, args):
        node = { 'type': 'CONTINUE' }
        self.next(node)

    def consume_label (self, args):
        node = { 'type': 'LABEL', 'name': args['name'] }
        self.next(node)
