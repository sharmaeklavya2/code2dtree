from __future__ import annotations
from collections.abc import Collection, Mapping, Sequence, Set
from typing import Any, Optional
from .expr import Var, Expr, BinExpr
from .aggExpr import AggExpr
from .rrtg import TreeExplorer


OSeq = Sequence[object]
OSeqColl = Collection[OSeq]


class LinCmpExpr(Expr):
    def __init__(self, coeffDict: Mapping[object, Any], op: str, rhs: Any):
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

    def negate(self) -> LinCmpExpr:
        return LinCmpExpr(self.coeffDict, NEG_OP[self.op], self.rhs)


NEG_OP = {
    '<': '≥',
    '>': '≤',
    '≥': '<',
    '≤': '>',
    '==': '≠',
    '≠': '==',
}


FLIP_OP_TO_G = {
    '>': ('>', 1),
    '≥': ('≥', 1),
    '==': ('==', 1),
    '<': ('>', -1),
    '≤': ('≥', -1),
}


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


def parseLinCmpExpr(expr: object) -> LinCmpExpr:
    if isinstance(expr, LinCmpExpr):
        return expr
    elif isinstance(expr, BinExpr):
        coeffDict: dict[object, Any] = {}
        op, baseCoeffMul = FLIP_OP_TO_G[expr.op]
        constTerm = 0
        for (coeffMul, subExpr) in ((baseCoeffMul, expr.larg), (-baseCoeffMul, expr.rarg)):
            constTerm += parseAffineHelper(subExpr, coeffMul, coeffDict)
        return LinCmpExpr(coeffDict, op, -constTerm)
    else:
        raise ValueError('expected BinExpr with comparison operator')


def domination(expr: LinCmpExpr, orderings: OSeqColl) -> Optional[bool]:
    # return True or False if we can infer expr's truth based on orderings, return None otherwise.
    if expr.op == '==':
        return None

    orderedVars: Set[object] = set()
    for ordering in orderings:
        orderedVars |= set(ordering)
    unorderedVars = expr.coeffDict.keys() - orderedVars

    allPos = all([expr.coeffDict[varName] >= 0 for varName in unorderedVars])
    allNeg = all([expr.coeffDict[varName] <= 0 for varName in unorderedVars])
    for ordering in orderings:
        coeffSum = 0
        for varName in ordering:
            if not (allPos or allNeg):
                return None
            coeffSum += expr.coeffDict.get(varName, 0)
            if coeffSum < 0:
                allPos = False
            if coeffSum > 0:
                allNeg = False

    rhs = expr.rhs
    if expr.op in ('<', '≤'):
        allPos, allNeg, rhs = allNeg, allPos, -rhs

    if allPos and rhs <= 0:
        return True
    if allNeg and rhs >= 0:
        return False
    return None


class LinConstrTreeExplorer(TreeExplorer):
    def __init__(self, orderings: OSeqColl = ()) -> None:
        super().__init__()
        self.orderings = orderings
        self.cache: dict[object, bool] = {}

    def noteIf(self, expr: Expr, b: bool) -> None:
        lce = parseLinCmpExpr(expr)
        self.cache[lce.key()] = b

    def decideIf(self, expr: Expr) -> tuple[bool, bool]:
        linCmpExpr = parseLinCmpExpr(expr)
        key = linCmpExpr.key()
        try:
            b = self.cache[key]
            return (b, False)
        except KeyError:
            domB = domination(linCmpExpr, self.orderings)
            if domB is not None:
                self.cache[key] = domB
                return (domB, False)
            else:
                self.cache[key] = False
                return (False, True)

    def noteReturn(self, expr: object) -> None:
        self.cache.clear()
