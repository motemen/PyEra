#!/usr/bin/env python

import re

class Parser:
    FUNCNAME = r'\w+'
    VARNAME  = r'\w+(?::\d+)?'
    OPLET    = r'[+-/*|]?='

    RE_FUNC_DECL   = re.compile(r'^@(?P<funcname>%s)$' % FUNCNAME)
    RE_LET         = re.compile(r'^(?P<lhs>%s)\s*(?P<op>%s)\s*(?P<rhs>.+)$' % ( VARNAME, OPLET ))
    RE_FUNC_CALL   = re.compile(r'^(?P<funcname>%s)\s+(?P<args>.*)$' % FUNCNAME)
    RE_STMT_IF     = re.compile(r'^IF\s+(?P<expr>.+)$')
    RE_STMT_ELSE   = re.compile(r'^ELSE$')
    RE_STMT_ELSEIF = re.compile(r'^ELSEIF\s+(?P<expr>.+)$')
    RE_STMT_ENDIF  = re.compile(r'^ENDIF$')

    CONSUME_RULES = [
        ( RE_FUNC_DECL,   'consume_func_decl' ),
        ( RE_LET,         'consume_let' ),
        ( RE_STMT_IF,     'consume_stmt_if' ),
        ( RE_STMT_ELSEIF, 'consume_stmt_elseif' ),
        ( RE_STMT_ELSE,   'consume_stmt_else' ),
        ( RE_STMT_ENDIF,  'consume_stmt_endif' ),
        ( RE_FUNC_CALL,   'consume_func_call' ),
    ]

    def __init__ (self):
        self.functions = {}
        self.next = None

    def parse (self, source):
        lines = source.split("\n")

        for line in lines:
            import re # ???
            line = re.sub(r';.*$', '', line)
            line = re.sub(r'^\s+', '', line)

            if len(line) == 0:
                continue

            for (re, c) in self.CONSUME_RULES:
                m = re.match(line)
                if m:
                    getattr(self, c)(m.groupdict())
                    break
            else:
                print 'Could not parse:', line

    def consume_func_decl (self, args):
        node = { 'type': 'FUNCTION', 'body': [] }
        self.functions[ args['funcname'] ] = node
        self.next = lambda n: node['body'].append(n)

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
                        # TODO
                        pass
                    else:
                        node['else'].append(n)
                self.next = _
            elif n['type'] == 'ENDIF':
                # TODO
                pass
            else:
                node['cond'][-1][1].append(n)
        self.next = _

    def consume_stmt_elseif (self, args):
        node = { 'type': 'ELSEIF', 'expr': args['expr'] }
        self.next(node)

    def consume_stmt_else (self, args):
        node = { 'type': 'ELSE' }
        self.next(node)

    def consume_stmt_endif (self, args):
        node = { 'type': 'ENDIF' }
        self.next(node)
