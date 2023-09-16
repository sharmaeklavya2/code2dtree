from collections.abc import Collection, Mapping, Sequence, Set
from typing import Any, Optional
from .expr import Var, Expr, BinExpr
from .aggExpr import AggExpr


class LinCmpExpr(Expr):
    def __init__(self, coeffDict: Mapping[object, Any], rhs: Any, op: str):
        self.coeffDict = coeffDict
        self.rhs = rhs
        self.op = op

    def __repr__(self) -> str:
        return '{}({}, op={}, rhs={})'.format(
            self.__class__.__name__, self.coeffDict, repr(self.op), repr(self.rhs))

    def __str__(self) -> str:
        terms = []
        for i, (varName, coeff) in enumerate(self.coeffDict.items()):
            if coeff != 0:
                signStr = '- ' if coeff < 0 else ('+ ' if i > 0 else '')
                coeff = -coeff if coeff < 0 else coeff
                coeffStr = str(coeff) if coeff != 1 else ''
                terms.append(signStr + coeffStr + str(varName))
        return ' '.join(terms) + ' {} {}'.format(self.op, str(self.rhs))

    def key(self) -> object:
        return (self.__class__.__name__, self.op, self.rhs, frozenset(self.coeffDict.items()))


def flipOpToG(op: str) -> tuple[str, int]:
    if op in ('>', '≥', '=='):
        return (op, 1)
    elif op == '<':
        return ('>', -1)
    elif op == '≤':
        return ('≥', -1)
    else:
        raise ValueError('invalid operator ' + op)


def addToDict(d: dict[object, Any], k: object, v: Any) -> None:
    try:
        d[k] += v
    except KeyError:
        d[k] = v


def parseAffineHelper(expr: object, coeffMul: Any, coeffDict: dict[object, Any]) -> Any:
    if isinstance(expr, Var):
        addToDict(coeffDict, expr.name, coeffMul)
        return 0
    elif isinstance(expr, BinExpr):
        if expr.op == '+':
            return (parseAffineHelper(expr.larg, coeffMul, coeffDict)
                + parseAffineHelper(expr.rarg, coeffMul, coeffDict))
        elif expr.op == '-':
            return (parseAffineHelper(expr.larg, coeffMul, coeffDict)
                + parseAffineHelper(expr.rarg, -coeffMul, coeffDict))
        elif expr.op == '*':
            isLExpr = isinstance(expr.larg, Expr)
            isRExpr = isinstance(expr.rarg, Expr)
            if isLExpr and isRExpr:
                raise ValueError('parseAffineHelper: encountered product of expressions')
            elif isLExpr:
                return parseAffineHelper(expr.larg, coeffMul * expr.rarg, coeffDict)
            elif isRExpr:
                return parseAffineHelper(expr.rarg, coeffMul * expr.larg, coeffDict)
            else:
                raise ValueError('parseAffineHelper: encountered product of non-expressions')
        else:
            raise ValueError('parseAffineHelper: unsupported operator ' + expr.op)
    elif isinstance(expr, AggExpr):
        if expr.op == '+':
            return sum([parseAffineHelper(arg, coeffMul, coeffDict) for arg in expr.args])
        else:
            raise ValueError('parseAffineHelper: unsupported AggExpr operator ' + expr.op)
    elif isinstance(expr, Expr):
        raise ValueError('parseAffineHelper: unknown Expr type ' + type(expr).__name__)
    else:
        return expr * coeffMul


def parseLinCmpExpr(expr: Expr) -> LinCmpExpr:
    if isinstance(expr, LinCmpExpr):
        return expr
    elif isinstance(expr, BinExpr):
        coeffDict: dict[object, Any] = {}
        op, baseCoeffMul = flipOpToG(expr.op)
        constTerm = 0
        for (coeffMul, subExpr) in ((baseCoeffMul, expr.larg), (-baseCoeffMul, expr.rarg)):
            constTerm += parseAffineHelper(subExpr, coeffMul, coeffDict)
        return LinCmpExpr(coeffDict, -constTerm, op)
    else:
        raise ValueError('expected BinExpr with comparison operator')


def parseLinCmpExpr(expr: Expr, varNames: Sequence[object]) -> LinCmpExpr:
    varNameToIndex = {varName: i for i, varName in enumerate(varNames)}
    coeffDict, op, constTerm = parseLinCmpExprHelper(expr)
    coeffs = [0] * len(varNames)
    for varName, coeff in coeffDict.items():
        coeffs[varNameToIndex[varName]] = coeff
    return LinCmpExpr(varNames, coeffs, constTerm, op)
