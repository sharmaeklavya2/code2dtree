from __future__ import annotations
from collections.abc import Iterable, Sequence
from typing import Union

from .expr import Expr, BinExpr


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
