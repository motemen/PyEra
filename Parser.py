#!/usr/bin/env python

import re

class Parser:
    FUNCNAME = r'\w+'
    LITERAL  = r'-?\d+'
    VARNAME  = r'\w+(?::\d+)?'
    OPLET    = r'[+-/*|]?='

    RE_FUNC_DECL   = re.compile(r'^@(?P<funcname>%s)$' % FUNCNAME)
    RE_FUNC_PROP   = re.compile(r'^#(?P<prop>\w+)$')
    RE_LET         = re.compile(r'^(?P<lhs>%s)\s*(?P<op>%s)\s*(?P<rhs>.+)$' % ( VARNAME, OPLET ))
    RE_FUNC_CALL   = re.compile(r'^(?P<funcname>%s)\s*(?P<args>.*)$' % FUNCNAME)

    RE_STMT_IF     = re.compile(r'^IF\s+(?P<expr>.+)$')
    RE_STMT_ELSE   = re.compile(r'^ELSE$')
    RE_STMT_ELSEIF = re.compile(r'^ELSEIF\s+(?P<expr>.+)$')
    RE_STMT_ENDIF  = re.compile(r'^ENDIF$')

    # expr
    RE_VALUE       = re.compile(r'^(?:%s|%s)' % ( LITERAL, VARNAME ))

    OP = [
        [ '||' ],
        [ '&&' ],
        [ '<', '<=', '>', '>=', '==', '!=' ],
        [ '+', '-' ],
        [ '*', '/' ]
    ]

    RE_OP = [
        re.compile(r'\|\|'),
        re.compile(r'&&'),
        re.compile(r'<=?|>=?|==|!='),
        re.compile(r'\+|-'),
        re.compile(r'\*|/')
    ]

    CONSUME_RULES = [
        ( RE_FUNC_DECL,   'consume_func_decl' ),
        ( RE_FUNC_PROP,   'consume_func_prop' ),
        ( RE_LET,         'consume_let' ),
        ( RE_STMT_IF,     'consume_stmt_if' ),
        ( RE_STMT_ELSEIF, 'consume_stmt_elseif' ),
        ( RE_STMT_ELSE,   'consume_stmt_else' ),
        ( RE_STMT_ENDIF,  'consume_stmt_endif' ),
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

    def parse_expr (self, expr, depth = 0):
        if depth >= len(self.OP):
            expr = re.sub('^\s*', '', expr)
            m = self.RE_VALUE.match(expr)
            token = m.group()
            return (token, expr[m.end():])

        (token, expr) = self.parse_expr(expr, depth + 1)
        expr = re.sub('^\s*', '', expr)

        re_op = self.RE_OP[depth]
        m = re_op.match(expr)
        if m == None:
            return (token, expr)

        op = m.group()
        expr = expr[m.end():]
        (token2, expr) = self.parse_expr(expr, depth)
        return ( { 'operator': op, 'operand': [ token, token2 ] }, expr )

    def consume_func_decl (self, args):
        node = { 'type': 'FUNCTION', 'body': [] }
        self.clear()
        self.functions[ args['funcname'] ] = node
        self.push(lambda n: node['body'].append(n))

    def consume_func_prop (self, args):
        pass

    def consume_let (self, args):
        node = { 'type': 'LET', 'lhs': args['lhs'], 'op': args['op'], 'rhs': args['rhs'] }
        self.next(node)

    def consume_func_call (self, args):
        node = { 'type': 'FUNC_CALL', 'funcname': args['funcname'], 'args': args['args'] }
        self.next(node)

    def consume_stmt_if (self, args):
        node = { 'type': 'IF', 'cond': [ ( args['expr'], [] ) ], 'else': [] }
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
        node = { 'type': 'ELSEIF', 'expr': args['expr'] }
        self.next(node)

    def consume_stmt_else (self, args):
        node = { 'type': 'ELSE' }
        self.next(node)

    def consume_stmt_endif (self, args):
        node = { 'type': 'ENDIF' }
        self.next(node)
