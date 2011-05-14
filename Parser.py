#!/usr/bin/env python

import re

class ParseException:
    def __init__ (self, msg):
        self.msg = msg

    def __repr__ (self):
        return self.msg

class Parser:
    FUNCNAME = r'\w+'
    LITERAL  = r'-?\d+'
    VARNAME  = r'\w+(?::\w+)?'
    OPLET    = r'[+-/*|]?='

    RE_FUNC_DECL   = re.compile(r'^@(?P<funcname>%s)$' % FUNCNAME)
    RE_FUNC_PROP   = re.compile(r'^#(?P<prop>\w+)$')
    RE_LET         = re.compile(r'^(?P<lhs>%s)\s*(?P<op>%s)\s*(?P<rhs>.+)$' % ( VARNAME, OPLET ))
    RE_FUNC_CALL   = re.compile(r'^(?P<funcname>%s)\s*(?P<args>.*)$' % FUNCNAME)

    RE_STMT_IF     = re.compile(r'^IF\s+(?P<expr>.+)$')
    RE_STMT_ELSE   = re.compile(r'^ELSE$')
    RE_STMT_ELSEIF = re.compile(r'^ELSEIF\s+(?P<expr>.+)$')
    RE_STMT_ENDIF  = re.compile(r'^ENDIF$')
    RE_STMT_SIF    = re.compile(r'^SIF\s+(?P<expr>.+)$')
    RE_STMT_REPEAT = re.compile(r'^REPEAT\s+(?P<expr>.+)$')
    RE_STMT_REND   = re.compile(r'^REND$')

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
        ( RE_STMT_SIF,    'consume_stmt_sif' ),

        ( RE_STMT_REPEAT, 'consume_stmt_repeat' ),
        ( RE_STMT_REND,   'consume_stmt_rend' ),

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

    def parse_expr (self, expr):
        (token, rest) = self._parse_expr(expr)
        if len(rest) > 0:
            raise ParseException('Parse remaining: ' + rest)
        return token

    def _parse_expr (self, expr, depth = 0):
        expr = re.sub(r'^\s*', '', expr)

        # '(' expr ')'
        if re.match(r'^\(', expr):
            (token, expr) = self._parse_expr(expr[1:])

        # value
        elif depth >= len(self.OP):
            m = self.RE_VALUE.match(expr)
            if m == None:
                raise ParseException('Expected literal: ' + expr)
            token = m.group()
            return (token, expr[m.end():])

        # term     ::= factor '*' term
        # expr_{n} ::= expr_{n+1} {op} expr_{n}
        else:
            (token, expr) = self._parse_expr(expr, depth + 1)
            expr = re.sub('^\s*', '', expr)

        m = self.RE_OP[depth].match(expr)
        if m == None:
            if re.match(r'^\)', expr):
                expr = expr[1:]
            return (token, expr)

        op = m.group()
        expr = expr[m.end():]
        (token2, expr) = self._parse_expr(expr, depth)

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
