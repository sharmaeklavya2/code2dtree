# coding: utf-8

from collections.abc import Iterable, Mapping


# [ Expr ] ====================================================================

class Expr:
    globalDTreeGen = None

    def key(self):
        raise NotImplementedError()

    def __hash__(self):
        return 0

    def __bool__(self):
        if Expr.globalDTreeGen is not None:
            return Expr.globalDTreeGen.reportFork(self)
        else:
            raise NotImplementedError("forking on expressions is disabled.")


class BinExpr(Expr):
    def __init__(self, op, larg, rarg):
        self.op = op
        self.larg = larg
        self.rarg = rarg

    def __repr__(self):
        return '{}({}, {}, {})'.format(self.__class__.__name__, repr(self.op),
            repr(self.larg), repr(self.rarg))

    def __str__(self):
        return '({} {} {})'.format(str(self.larg), str(self.op), str(self.rarg))

    def key(self):
        return (self.__class__.__name__, self.op, self.larg.key(), self.rarg.key())


class Var(Expr):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __str__(self):
        return self.name

    def key(self):
        return (self.__class__.__name__, self.name)


BIN_OPS = {
    '+': 'add',
    '-': 'sub',
    '*': 'mul',
    '@': 'matmul',
    '/': 'truediv',
    '//': 'floordiv',
    '%': 'mod',
    '**': 'pow',
    '>>': 'lshift',
    '<<': 'rshift',
    '<': 'lt',
    '≤': 'le',
    '>': 'gt',
    '≥': 'ge',
    '==': 'eq',
    '≠': 'ne',
}


def getBinMethods(op):
    def binMethod(self, other):
        return BinExpr(op, self, other)

    def rbinMethod(self, other):
        return BinExpr(op, other, self)

    return (binMethod, rbinMethod)


def overloadOps():
    for op, pyopname in BIN_OPS.items():
        func, rfunc = getBinMethods(op)
        setattr(Expr, '__' + pyopname + '__', func)
        setattr(Expr, '__r' + pyopname + '__', rfunc)


overloadOps()


def prettyExprRepr(x):
    if isinstance(x, str):
        return repr(x)
    elif isinstance(x, Expr):
        s = str(x)
        return s[1:-1] if s[0] == '(' else s
    elif isinstance(x, Iterable):
        csv = ', '.join([prettyExprRepr(y) for y in x])
        if isinstance(x, tuple):
            return '(' + csv + ')'
        elif isinstance(x, set):
            return '{' + csv + '}'
        elif isinstance(x, list):
            return '[' + csv + ']'
        else:
            return '{}([{}])'.format(x.__class__.__name__, csv)
    elif isinstance(x, Mapping):
        return '{' + ', '.join([prettyExprRepr(k) + ': ' + prettyExprRepr(v)
            for k, v in x.items()]) + '}'
    else:
        return repr(x)


# [ DNode ] ===================================================================

class DNode:
    def __init__(self, expr, parent):
        self.expr = expr
        self.parent = parent

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.expr)

    def print(self, fp, indent=0):
        print('  ' * indent + 'return ' + prettyExprRepr(self.expr), file=fp)


class DINode(DNode):
    def __init__(self, expr, parent):
        super().__init__(expr, parent)
        self.children = [None, None]

    def __repr__(self):
        return '{}({}, 0={}, 1={})'.format(self.__class__.__name__, self.expr,
            self.children[0], self.children[1])

    def print(self, fp, indent=0):
        print('  ' * indent + 'if ' + prettyExprRepr(self.expr) + ':', file=fp)
        noneString = '  ' * (indent + 1) + 'unfinished'
        if self.children[1] is None:
            print(noneString, file=fp)
        else:
            self.children[1].print(fp, indent+1)
        print('  ' * indent + 'else:')
        if self.children[0] is None:
            print(noneString, file=fp)
        else:
            self.children[0].print(fp, indent+1)


def toVE(root):
    V = []
    E = []
    id = 0

    def explore(u, ui):
        nonlocal id
        V.append(u)
        if isinstance(u, DINode):
            if u.children[0] is not None:
                id += 1
                vi = id
                E.append((ui, vi, 0))
                explore(u.children[0], vi)
            if u.children[1] is not None:
                id += 1
                vi = id
                E.append((ui, vi, 1))
                explore(u.children[1], vi)

    explore(root, 0)
    return (V, E)


def printGraphViz(V, E, fp):
    print('digraph DTree{', file=fp)
    for i, v in enumerate(V):
        print('v{} [label="{}"];'.format(i, prettyExprRepr(v.expr)), file=fp)
    for (u, v, label) in E:
        print('v{} -> v{} [label="{}"];'.format(u, v, label), file=fp)
    print('}', file=fp)


# [ RepeatedRunDTreeGen ] =====================================================


class RepeatedRunDTreeGen:
    def __init__(self, useCache=True):
        self.depth = 0
        self.root = None
        self.activeLeaf = None
        self.boolStack = []
        self.finished = False
        self.useCache = useCache
        self.cachedValues = {}
        """
        Let c be the nodes consisting of self.activeLeaf and its ancestors, ordered root-first.
        Then len(c) == len(self.boolStack), and self.boolStack[i] is the value of c.expr.
        """

    def __repr__(self):
        return 'RRDTG(depth={}, root={}, aLeaf={}, bstk={}, fin={})'.format(self.depth,
            repr(self.root), repr(self.activeLeaf), repr(self.boolStack), self.finished)

    def reportFork(self, expr):
        assert not(self.finished)
        assert self.depth <= len(self.boolStack)
        if self.useCache:
            try:
                return self.cachedValues[expr.key()]
            except KeyError:
                pass
        if self.depth == len(self.boolStack):
            node = DINode(expr, self.activeLeaf)
            if self.activeLeaf is not None:
                self.activeLeaf.children[self.boolStack[-1]] = node
            else:
                self.root = node
            self.activeLeaf = node
            self.boolStack.append(False)
        result = self.boolStack[self.depth]
        if self.useCache:
            self.cachedValues[expr.key()] = result
        self.depth += 1
        return result

    def reportEnd(self, expr):
        assert not(self.finished)
        assert self.depth == len(self.boolStack)
        node = DNode(expr, self.activeLeaf)
        if self.activeLeaf is not None:
            self.activeLeaf.children[self.boolStack[-1]] = node
        else:
            self.root = node

        while len(self.boolStack) and self.boolStack[-1]:
            self.boolStack.pop()
            self.activeLeaf = self.activeLeaf.parent
        if len(self.boolStack):
            self.boolStack[-1] = True
        else:
            self.finished = True
        if self.useCache:
            self.cachedValues.clear()
        self.depth = 0

    def runOnce(self, func, *args, **kwargs):
        Expr.globalDTreeGen = self
        result = func(*args, **kwargs)
        self.reportEnd(result)
        Expr.globalDTreeGen = None

    def run(self, func, *args, **kwargs):
        Expr.globalDTreeGen = self
        while not(self.finished):
            result = func(*args, **kwargs)
            self.reportEnd(result)
        Expr.globalDTreeGen = None
