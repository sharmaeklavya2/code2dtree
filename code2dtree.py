# coding: utf-8

from __future__ import annotations
import sys
from collections.abc import Iterable, Mapping
from typing import Callable, Optional, TextIO


# [ Expr ] ====================================================================

class Expr:
    globalDTreeGen: Optional[RepeatedRunDTreeGen] = None

    def key(self) -> object:
        raise NotImplementedError()

    def __hash__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        if Expr.globalDTreeGen is not None:
            return Expr.globalDTreeGen.reportFork(self)
        else:
            raise NotImplementedError("forking on expressions is disabled.")


class BinExpr(Expr):
    def __init__(self, op: str, larg: Expr, rarg: Expr):
        self.op = op
        self.larg = larg
        self.rarg = rarg

    def __repr__(self) -> str:
        return '{}({}, {}, {})'.format(self.__class__.__name__, repr(self.op),
            repr(self.larg), repr(self.rarg))

    def __str__(self) -> str:
        return '({} {} {})'.format(str(self.larg), str(self.op), str(self.rarg))

    def key(self) -> object:
        return (self.__class__.__name__, self.op, self.larg.key(), self.rarg.key())


class Var(Expr):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __str__(self) -> str:
        return self.name

    def key(self) -> object:
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


BinExprFunc = Callable[[Expr, Expr], BinExpr]


def getBinMethods(op: str) -> tuple[BinExprFunc, BinExprFunc]:
    def binMethod(self: Expr, other: Expr) -> BinExpr:
        return BinExpr(op, self, other)

    def rbinMethod(self: Expr, other: Expr) -> BinExpr:
        return BinExpr(op, other, self)

    return (binMethod, rbinMethod)


def overloadOps() -> None:
    for op, pyopname in BIN_OPS.items():
        func, rfunc = getBinMethods(op)
        setattr(Expr, '__' + pyopname + '__', func)
        setattr(Expr, '__r' + pyopname + '__', rfunc)


overloadOps()


def prettyExprRepr(x: object) -> str:
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


# [ Node ] ===================================================================

class Node:
    def __init__(self, expr: object, parent: Optional[InternalNode], explored: bool):
        self.expr = expr
        self.parent = parent
        self.explored = explored

    def __repr__(self) -> str:
        return '{}({}, exp={})'.format(self.__class__.__name__, self.expr, self.explored)

    def print(self, fp: TextIO, indent: int = 0) -> None:
        raise NotImplementedError()


class LeafNode(Node):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent, True)


class ReturnNode(LeafNode):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent)

    def print(self, fp: TextIO, indent: int = 0) -> None:
        print('  ' * indent + 'return ' + prettyExprRepr(self.expr), file=fp)


class NothingNode(LeafNode):
    def __init__(self, parent: Optional[InternalNode]):
        super().__init__(None, parent)

    def print(self, fp: TextIO, indent: int = 0) -> None:
        print('  ' * indent + '(nothing)')


class InternalNode(Node):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent, False)
        self.kids: Iterable[Optional[Node]] = []


class IfNode(InternalNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode]):
        super().__init__(expr, parent)
        self.kids: list[Optional[Node]] = [None] * 2

    def __repr__(self) -> str:
        return '{}({}, 0={}, 1={})'.format(self.__class__.__name__, self.expr,
            self.kids[0], self.kids[1])

    def print(self, fp: TextIO, indent: int = 0) -> None:
        noneString = '  ' * (indent + 1) + '(unfinished)'
        print('  ' * indent + 'if ' + prettyExprRepr(self.expr) + ':', file=fp)
        if self.kids[1] is None:
            print(noneString, file=fp)
        else:
            self.kids[1].print(fp, indent+1)
        print('  ' * indent + 'else:')
        if self.kids[0] is None:
            print(noneString, file=fp)
        else:
            self.kids[0].print(fp, indent+1)


GraphEdge = tuple[int, int, int]


def toVE(root: Optional[Node]) -> tuple[list[Node], list[GraphEdge]]:
    V = []
    E = []
    id = 0

    def explore(u: Node, ui: int) -> None:
        nonlocal id
        V.append(u)
        if isinstance(u, InternalNode):
            for j, v in enumerate(u.kids):
                if v is not None:
                    id += 1
                    vi = id
                    E.append((ui, vi, j))
                    explore(v, vi)

    if root is not None:
        explore(root, 0)
    else:
        print('Warning: empty tree passed to toVE', file=sys.stderr)
    return (V, E)


def printGraphViz(V: list[Node], E: list[GraphEdge], fp: TextIO) -> None:
    print('digraph DTree{', file=fp)
    for i, w in enumerate(V):
        print('v{} [label="{}"];'.format(i, prettyExprRepr(w.expr)), file=fp)
    for (u, v, label) in E:
        print('v{} -> v{} [label="{}"];'.format(u, v, label), file=fp)
    print('}', file=fp)


# [ RepeatedRunDTreeGen ] =====================================================


class RepeatedRunDTreeGen:
    def __init__(self, useCache: bool = True):
        self.depth = 0
        self.root: Optional[Node] = None
        self.activeLeaf: Optional[InternalNode] = None
        self.boolStack: list[bool] = []
        self.finished = False
        self.useCache = useCache
        self.cachedValues: dict[object, bool] = {}
        """
        Let c be the nodes consisting of self.activeLeaf and its ancestors, ordered root-first.
        Then len(c) == len(self.boolStack), and self.boolStack[i] is the value of c[i].expr.
        """

    def __repr__(self) -> str:
        return 'RRDTG(depth={}, root={}, aLeaf={}, bstk={}, fin={})'.format(self.depth,
            repr(self.root), repr(self.activeLeaf), repr(self.boolStack), self.finished)

    def reportFork(self, expr: Expr) -> bool:
        assert not(self.finished)
        assert self.depth <= len(self.boolStack)
        if self.useCache:
            try:
                return self.cachedValues[expr.key()]
            except KeyError:
                pass
        if self.depth == len(self.boolStack):
            node = IfNode(expr, self.activeLeaf)
            if self.activeLeaf is not None:
                assert isinstance(self.activeLeaf, IfNode)
                self.activeLeaf.kids[self.boolStack[-1]] = node
            else:
                self.root = node
            self.activeLeaf = node
            self.boolStack.append(False)
        result = self.boolStack[self.depth]
        if self.useCache:
            self.cachedValues[expr.key()] = result
        self.depth += 1
        return result

    def reportEnd(self, expr: object) -> None:
        assert not(self.finished)
        assert self.depth == len(self.boolStack)
        node = ReturnNode(expr, self.activeLeaf)
        if self.activeLeaf is not None:
            assert isinstance(self.activeLeaf, IfNode)
            self.activeLeaf.kids[self.boolStack[-1]] = node
        else:
            self.root = node

        while len(self.boolStack) and self.boolStack[-1]:
            assert self.activeLeaf is not None  # since boolStack is not empty
            self.boolStack.pop()
            self.activeLeaf = self.activeLeaf.parent
        if len(self.boolStack):
            self.boolStack[-1] = True
        else:
            self.finished = True
        if self.useCache:
            self.cachedValues.clear()
        self.depth = 0

    def runOnce(self, func: Callable[..., object], *args: object, **kwargs: object) -> None:
        Expr.globalDTreeGen = self
        result = func(*args, **kwargs)
        self.reportEnd(result)
        Expr.globalDTreeGen = None

    def run(self, func: Callable[..., object], *args: object, **kwargs: object) -> None:
        Expr.globalDTreeGen = self
        while not(self.finished):
            result = func(*args, **kwargs)
            self.reportEnd(result)
        Expr.globalDTreeGen = None


def func2dtree(func: Callable[..., object], *args: object, **kwargs: object) -> Node:
    gen = RepeatedRunDTreeGen()
    gen.run(func, *args, **kwargs)
    assert gen.root is not None
    return gen.root
