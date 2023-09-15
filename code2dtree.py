# coding: utf-8

from __future__ import annotations
import sys
from collections.abc import Iterable, Mapping, MutableSequence, Sequence
from typing import Callable, Optional, TextIO, Union


# [ Expr ] ====================================================================

class Expr:
    globalTreeGen: Optional[RepeatedRunTreeGen] = None

    def key(self) -> object:
        raise NotImplementedError()

    def __hash__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        if Expr.globalTreeGen is not None:
            return Expr.globalTreeGen.decideIf(self)
        else:
            raise NotImplementedError("forking on expressions is disabled.")


class BinExpr(Expr):
    def __init__(self, op: str, larg: object, rarg: object):
        super().__init__()
        self.op = op
        self.larg = larg
        self.rarg = rarg

    def __repr__(self) -> str:
        return '{}({}, {}, {})'.format(self.__class__.__name__, repr(self.op),
            repr(self.larg), repr(self.rarg))

    def __str__(self) -> str:
        return '({} {} {})'.format(str(self.larg), str(self.op), str(self.rarg))

    def key(self) -> object:
        lkey = self.larg.key() if isinstance(self.larg, Expr) else self.larg
        rkey = self.rarg.key() if isinstance(self.rarg, Expr) else self.rarg
        return (self.__class__.__name__, self.op, lkey, rkey)


class AggExpr(Expr):
    def __init__(self, op: str, args: Sequence[object]):
        super().__init__()
        self.op = op
        self.args = args

    def __repr__(self) -> str:
        return '{}({}, {})'.format(self.__class__.__name__, repr(self.op), repr(self.args))

    def __str__(self) -> str:
        sep = ' ' + self.op + ' '
        return '(' + sep.join([str(x) for x in self.args]) + ')'

    def key(self) -> object:
        argKeys = tuple([x.key() if isinstance(x, Expr) else x for x in self.args])
        return (self.__class__.__name__, self.op, argKeys)


class Var(Expr):
    def __init__(self, name: object):
        super().__init__()
        self.name = name

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __str__(self) -> str:
        return str(self.name)

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


# [ Utilities ]=================================================================

def flattenExprHelper(expr: object, op: str, output: list[object]) -> None:
    if isinstance(expr, BinExpr):
        if expr.op == op:
            flattenExprHelper(expr.larg, op, output)
            flattenExprHelper(expr.rarg, op, output)
        else:
            output.append(expr)
    elif isinstance(expr, AggExpr):
        if expr.op == op:
            for arg in expr.args:
                flattenExprHelper(arg, op, output)
        else:
            output.append(expr)
    else:
        output.append(expr)


def flattenExpr(expr: object, op: str) -> AggExpr:
    terms: list[object] = []
    flattenExprHelper(expr, op, terms)
    return AggExpr(op, terms)


def all(it: Iterable[object]) -> Union[bool, AggExpr]:
    terms: list[Expr] = []
    for x in it:
        if isinstance(x, Expr):
            terms.append(x)
        elif not x:
            return False
    return AggExpr('and', terms)


def any(it: Iterable[object]) -> Union[bool, AggExpr]:
    terms: list[Expr] = []
    for x in it:
        if isinstance(x, Expr):
            terms.append(x)
        elif x:
            return True
    return AggExpr('or', terms)


# [ Node ] =====================================================================

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
    def __init__(self, expr: object, parent: Optional[InternalNode], nKids: int):
        super().__init__(expr, parent, False)
        self.kids: MutableSequence[Optional[Node]] = [None] * nKids

    def getKidsExploreStatus(self) -> tuple[int, int]:
        nEKids, nKids = 0, 0
        for kid in self.kids:
            nKids += 1
            nEKids += kid is not None and kid.explored
        return (nEKids, nKids)

    def setExploreStatusRec(self) -> None:
        nEKids, nKids = self.getKidsExploreStatus()
        if nEKids == nKids:
            self.explored = True
            if self.parent is not None:
                self.parent.setExploreStatusRec()

    def __repr__(self) -> str:
        parts = ['{}({}'.format(self.__class__.__name__, self.expr)]
        for i, kid in enumerate(self.kids):
            parts.append('{}={}'.format(i, kid))
        return ', '.join(parts) + ')'


class IfNode(InternalNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode]):
        super().__init__(expr, parent, 2)

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


class FrozenIfNode(InternalNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode], b: bool):
        super().__init__(expr, parent, 1)
        self.b = b

    def print(self, fp: TextIO, indent: int = 0) -> None:
        noneString = '  ' * (indent + 1) + '(unfinished)'
        print('  ' * indent + 'assert ' + ('' if self.b else 'not(') +
            prettyExprRepr(self.expr) + ('' if self.b else ')'))
        if self.kids[0] is None:
            print(noneString, file=fp)
        else:
            self.kids[0].print(fp, indent)


GraphEdge = tuple[int, int, int]


def toVE(root: Optional[Node]) -> tuple[list[Node], list[GraphEdge]]:
    V = []
    E = []
    id = 0

    def explore(u: Node, ui: int) -> None:
        nonlocal id
        V.append(u)
        if isinstance(u, IfNode):
            for j, v in enumerate(u.kids):
                if v is not None:
                    id += 1
                    vi = id
                    E.append((ui, vi, j))
                    explore(v, vi)
        elif isinstance(u, FrozenIfNode):
            j, v = 0, u.kids[0]
            if v is not None:
                id += 1
                vi = id
                E.append((ui, vi, int(u.b)))
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


# [ RepeatedRunTreeGen ] =====================================================

class TreeExplorer:
    def decideIf(self, expr: Expr) -> tuple[bool, bool]:
        # return pair (b1, b2), where b1 = bool(expr) and b2 decides whether
        # not(expr) should be explored in the future.
        return (False, True)

    def noteIf(self, expr: Expr, b: bool) -> None:
        pass

    def noteReturn(self, expr: object) -> None:
        pass


class CachedTreeExplorer(TreeExplorer):
    def __init__(self) -> None:
        super().__init__()
        self.cache: dict[object, bool] = {}

    def noteIf(self, expr: Expr, b: bool) -> None:
        key = expr.key()
        self.cache[key] = b

    def decideIf(self, expr: Expr) -> tuple[bool, bool]:
        key = expr.key()
        try:
            b = self.cache[key]
            return (b, False)
        except KeyError:
            self.cache[key] = False
            return (False, True)

    def noteReturn(self, expr: object) -> None:
        self.cache.clear()


class RepeatedRunTreeGen:
    def __init__(self, explorer: TreeExplorer):
        self.explorer = explorer
        self.root: Optional[Node] = None
        self.parent: Optional[InternalNode] = None
        self.current: Optional[Node] = None
        self.kidIndex: Optional[int] = None

    def finished(self) -> bool:
        return self.root is not None and self.root.explored

    def __repr__(self) -> str:
        return 'RRDTG(root={})'.format(repr(self.root))

    def goDown(self, i: int) -> None:
        assert self.current is not None and isinstance(self.current, InternalNode)
        self.parent = self.current
        self.current = self.current.kids[i]
        self.kidIndex = i

    def decideIf(self, expr: Expr) -> bool:
        if self.current is not None:
            assert isinstance(self.current, IfNode) or isinstance(self.current, FrozenIfNode)
            kidStatuses = [kid is not None and kid.explored for kid in self.current.kids]
            assert sum(kidStatuses) < len(kidStatuses)
            if isinstance(self.current, IfNode):
                for b in (False, True):
                    if kidStatuses[not b]:
                        self.explorer.noteIf(expr, b)
                        self.goDown(b)
                        return b
            else:
                b = self.current.b
                self.explorer.noteIf(expr, b)
                self.goDown(0)
                return b

        # now all kids are unexplored and self.current is not a FrozenIfNode
        b, checkOther = self.explorer.decideIf(expr)
        if self.current is not None:
            assert isinstance(self.current, IfNode)
            if not checkOther:
                raise ValueError('TreeExplorer.decideIf outputs inconsistent checkOther for expr '
                    + str(expr))
            else:
                self.goDown(b)
                return b
        else:
            if checkOther:
                node: InternalNode = IfNode(expr, self.parent)
            else:
                node = FrozenIfNode(expr, self.parent, b)
            if self.parent is not None:
                assert self.kidIndex is not None
                self.parent.kids[self.kidIndex] = node
            else:
                self.root = node
            self.parent = node
            self.current = None
            self.kidIndex = b if checkOther else 0
            return b

    def reportEnd(self, expr: object) -> None:
        assert self.current is None
        node = ReturnNode(expr, self.parent)
        if self.parent is not None:
            assert self.kidIndex is not None
            self.parent.kids[self.kidIndex] = node
        else:
            self.root = node

        if self.parent is not None:
            self.parent.setExploreStatusRec()
        self.parent = None
        self.current = self.root
        self.kidIndex = None
        self.explorer.noteReturn(expr)

    def runOnce(self, func: Callable[..., object], *args: object, **kwargs: object) -> None:
        Expr.globalTreeGen = self
        result = func(*args, **kwargs)
        self.reportEnd(result)
        Expr.globalTreeGen = None

    def run(self, func: Callable[..., object], *args: object, **kwargs: object) -> None:
        Expr.globalTreeGen = self
        while not(self.finished()):
            result = func(*args, **kwargs)
            self.reportEnd(result)
        Expr.globalTreeGen = None


def func2dtree(func: Callable[..., object], *args: object, **kwargs: object) -> Node:
    gen = RepeatedRunTreeGen(CachedTreeExplorer())
    gen.run(func, *args, **kwargs)
    assert gen.root is not None
    return gen.root
