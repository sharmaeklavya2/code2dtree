from collections.abc import Mapping, Sequence
from typing import Any
from .expr import Var, Expr, BinExpr
from .aggExpr import AggExpr


class LinCmpExpr(Expr):
    def __init__(self, varNames: Sequence[object], coeffs: Sequence[Any], rhs: Any, op: str):
        if len(varNames) != len(coeffs):
            raise ValueError('len(varNames)={}, but len(coeffs)={}'.format(
                len(varNames), len(coeffs)))
        self.varNames = varNames
        self.coeffs = coeffs
        self.rhs = rhs
        self.op = op

    def __repr__(self) -> str:
        return '{cls}(varNames={varNames}, coeffs={coeffs}, op={op}, rhs={rhs})'.format(
            cls=self.__class__.__name__, varNames=repr(self.varNames), coeffs=repr(self.coeffs),
            op=repr(self.op), rhs=repr(self.rhs))

    def __str__(self) -> str:
        # return '({} {} {})'.format(str(self.larg), str(self.op), str(self.rarg))
        terms = []
        for i, (varName, coeff) in enumerate(zip(self.varNames, self.coeffs)):
            if coeff != 0:
                signStr = '- ' if coeff < 0 else ('+ ' if i > 0 else '')
                coeff = -coeff if coeff < 0 else coeff
                coeffStr = str(coeff) if coeff != 1 else ''
                terms.append(signStr + coeffStr + str(varName))
        return ' '.join(terms) + ' {} {}'.format(self.op, str(self.rhs))

    def key(self) -> object:
        return (self.__class__.__name__, self.op, self.rhs, tuple(self.coeffs),
            tuple(self.varNames))


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


def parseLinCmpExprHelper(expr: Expr) -> tuple[Mapping[object, Any], str, Any]:
    if isinstance(expr, BinExpr):
        coeffDict: dict[object, Any] = {}
        op, baseCoeffMul = flipOpToG(expr.op)
        constTerm = 0
        for (coeffMul, subExpr) in ((baseCoeffMul, expr.larg), (-baseCoeffMul, expr.rarg)):
            constTerm += parseAffineHelper(subExpr, coeffMul, coeffDict)
        return (coeffDict, op, -constTerm)
    else:
        raise ValueError('expected BinExpr with comparison operator')


def parseLinCmpExpr(expr: Expr, varNames: Sequence[object]) -> LinCmpExpr:
    varNameToIndex = {varName: i for i, varName in enumerate(varNames)}
    coeffDict, op, constTerm = parseLinCmpExprHelper(expr)
    coeffs = [0] * len(varNames)
    for varName, coeff in coeffDict.items():
        coeffs[varNameToIndex[varName]] = coeff
    return LinCmpExpr(varNames, coeffs, constTerm, op)
