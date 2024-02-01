from __future__ import annotations
from collections.abc import Iterable, Mapping, Sequence, Set
from typing import Optional, TextIO, TypeVar
from .expr import Var, Expr, BinExpr, UnExpr
from .aggExpr import AggExpr
from .treeExplorer import TreeExplorer
from .types import Real, validateRealness
from .interval import Interval

ORSet = Set[tuple[object, Real]]
ConstrMap = Mapping[ORSet, Interval]
ConstrDict = dict[ORSet, Interval]
T = TypeVar('T')

FLIP_OP = {  # x op y iff y FLIP_OP[op] x
    '>': '<',
    '≥': '≤',
    '<': '>',
    '≤': '≥',
}

NEG_OP = {  # x op y iff not(x NEG_OP[op] y)
    '>': '≤',
    '≥': '<',
    '<': '≥',
    '≤': '>',
}


def parseAffineHelper(expr: object, coeffMul: Real, coeffDict: dict[object, Real]) -> Real:
    if isinstance(expr, Var):
        try:
            coeffDict[expr.name] += coeffMul
        except KeyError:
            coeffDict[expr.name] = coeffMul
        return 0
    elif isinstance(expr, UnExpr):
        if expr.op == '+':
            return parseAffineHelper(expr.arg, coeffMul, coeffDict)
        elif expr.op == '-':
            return parseAffineHelper(expr.arg, -coeffMul, coeffDict)
        else:
            raise ValueError('parseAffineHelper: unsupported operator ' + expr.op)
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
                return parseAffineHelper(expr.larg, coeffMul * validateRealness(expr.rarg), coeffDict)
            elif isRExpr:
                return parseAffineHelper(expr.rarg, coeffMul * validateRealness(expr.larg), coeffDict)
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
        return validateRealness(expr) * coeffMul


def argReprMin(a: Iterable[T]) -> Optional[T]:
    minX = None
    minY: Optional[str] = None
    for x in a:
        y = repr(x)
        if minY is None or y < minY:
            minX, minY = x, y
    return minX


def canonicalizeDict(d: Mapping[object, Real]) -> tuple[Mapping[object, Real], bool]:
    minKey = argReprMin(d.keys())
    if minKey is None:  # d is empty
        return (d, False)
    else:
        if d[minKey] >= 0:
            return (d, False)
        else:
            return ({k: -v for k, v in d.items()}, True)


def parseLinCmpExpr(expr: Expr) -> tuple[Mapping[object, Real], str, Real]:
    if isinstance(expr, BinExpr) and expr.op in FLIP_OP.keys():
        coeffDict: dict[object, Real] = {}
        rhs = - (parseAffineHelper(expr.larg, 1, coeffDict)
            + parseAffineHelper(expr.rarg, -1, coeffDict))
        delKeys = [k for k, v in coeffDict.items() if v == 0]
        for k in delKeys:
            del coeffDict[k]
        coeffMap, flip = canonicalizeDict(coeffDict)
        del coeffDict
        if flip:
            op, rhs = FLIP_OP[expr.op], -rhs
        else:
            op = expr.op
        return (coeffMap, op, rhs)
    else:
        raise ValueError('expected BinExpr with comparison operator')


def opToInterval(op: str, v: Real) -> Interval:
    if op in ('<', '≤'):
        return Interval(None, v, False, op == '≤')
    else:
        return Interval(v, None, op == '≥', False)


def evalOp(larg: Real, op: str, rarg: Real) -> bool:
    if op == '<':
        return larg < rarg
    elif op == '>':
        return larg > rarg
    elif op == '≥':
        return larg >= rarg
    elif op == '≤':
        return larg <= rarg
    else:
        raise ValueError('invalid operator ' + op)


def addConstrToDict(expr: Expr, b: bool, d: ConstrDict) -> None:
    coeffDict, op, rhs = parseLinCmpExpr(expr)
    if not coeffDict:
        exprValue = evalOp(0, op, rhs)
        if exprValue != b:
            raise Exception("Entering impossible scenario.")
        return
    if not b:
        op = NEG_OP[op]
    coeffs = frozenset(coeffDict.items())
    oldInt = d.get(coeffs)
    newInt = opToInterval(op, rhs)
    if oldInt is None:
        d[coeffs] = newInt
    else:
        intersectInt = oldInt.intersect(newInt)
        if intersectInt.isEmpty():
            raise Exception("Entering impossible scenario.")
        else:
            d[coeffs] = intersectInt


def displayConstraints(d: ConstrMap, fp: TextIO) -> None:
    isFirst = True
    for coeffs, interval in d.items():
        lineParts = []
        for varName, coeff in coeffs:
            if coeff == 0:
                continue
            elif coeff < 0:
                lineParts.append('-')
                coeff = -coeff
            elif not isFirst:
                lineParts.append('+')
            if coeff != 1:
                lineParts.append(str(coeff))
                lineParts.append('*')
            lineParts.append(str(varName))
            isFirst = False
        lineParts.append('∈')
        lineParts.append(str(interval))
        print(' '.join(lineParts), file=fp)


class LinConstrTreeExplorer(TreeExplorer):
    def __init__(self, baseConstraintsList: Sequence[Expr] = ()) -> None:
        super().__init__()
        self.baseConstraintsDict: ConstrDict = {}
        for expr in baseConstraintsList:
            addConstrToDict(expr, True, self.baseConstraintsDict)
        self.constraints: ConstrDict = dict(self.baseConstraintsDict)

    def noteIf(self, expr: Expr, b: bool) -> None:
        addConstrToDict(expr, b, self.constraints)

    def decideIf(self, expr: Expr) -> tuple[bool, bool]:
        coeffDict, op, rhs = parseLinCmpExpr(expr)
        if not coeffDict:
            exprValue = evalOp(0, op, rhs)
            return (exprValue, False)
        coeffs = frozenset(coeffDict.items())
        oldInt = self.constraints.get(coeffs)
        falseInt, trueInt = opToInterval(NEG_OP[op], rhs), opToInterval(op, rhs)
        if oldInt is None:
            self.constraints[coeffs] = falseInt
            return (False, True)
        else:
            falseInt2, trueInt2 = oldInt.intersect(falseInt), oldInt.intersect(trueInt)
            if falseInt2.isEmpty():
                self.constraints[coeffs] = trueInt2
                return (True, False)
            else:
                self.constraints[coeffs] = falseInt2
                return (False, not trueInt2.isEmpty())

    def noteReturn(self, expr: object) -> None:
        self.constraints = dict(self.baseConstraintsDict)

    def displayConstraints(self, fp: TextIO) -> None:
        displayConstraints(self.constraints, fp)
