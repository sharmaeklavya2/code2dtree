# coding: utf-8

# [ Expr ] ====================================================================

class Expr:
    globalDTreeGen = None

    def __bool__(self):
        if Expr.globalDTreeGen is not None:
            return Expr.globalDTreeGen.reportFork(self)
        else:
            raise NotImplementedError("forking on expressions is not yet implemented")


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


class Var(Expr):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __str__(self):
        return self.name


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
    '≠': 'neq',
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


# [ DNode ] ===================================================================

class DNode:
    def __init__(self, expr, parent):
        self.expr = expr
        self.parent = parent

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.expr)

    def print(self, fp, indent=0):
        print('  ' * indent + 'return ' + str(self.expr), file=fp)


class DINode(DNode):
    def __init__(self, expr, parent):
        super().__init__(expr, parent)
        self.children = [None, None]

    def __repr__(self):
        return '{}({}, 0={}, 1={})'.format(self.__class__.__name__, self.expr,
            self.children[0], self.children[1])

    def print(self, fp, indent=0):
        print('  ' * indent + 'if ' + str(self.expr) + ':', file=fp)
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


# [ RepeatedRunDTreeGen ] =====================================================


class RepeatedRunDTreeGen:
    def __init__(self):
        self.depth = 0
        self.root = None
        self.activeLeaf = None
        self.boolStack = []
        self.finished = False

    def __repr__(self):
        return 'RRDTG(depth={}, root={}, aLeaf={}, bstk={}, fin={})'.format(self.depth,
            repr(self.root), repr(self.activeLeaf), repr(self.boolStack), self.finished)

    def reportFork(self, expr):
        assert not(self.finished)
        assert self.depth <= len(self.boolStack)
        if self.depth == len(self.boolStack):
            node = DINode(expr, self.activeLeaf)
            if self.activeLeaf is not None:
                self.activeLeaf.children[self.boolStack[-1]] = node
            else:
                self.root = node
            self.activeLeaf = node
            self.boolStack.append(False)
        result = self.boolStack[self.depth]
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
