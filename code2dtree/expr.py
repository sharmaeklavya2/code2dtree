from __future__ import annotations
from collections.abc import Iterable, Mapping
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .rrtg import RepeatedRunTreeGen


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


class Var(Expr):
    registry: dict[object, Var] = {}

    @staticmethod
    def get(name: object) -> Var:
        try:
            return Var.registry[name]
        except KeyError:
            return Var(name)

    def __init__(self, name: object):
        super().__init__()
        if name in Var.registry:
            raise Exception('{}({}) already exists'.format(self.__class__.__name__, repr(name)))
        else:
            self.name = name
            Var.registry[name] = self

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __str__(self) -> str:
        return str(self.name)

    def key(self) -> object:
        return (self.__class__.__name__, self.name)


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