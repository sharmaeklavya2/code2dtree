from collections.abc import Collection, Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from typing import Any, Literal, NamedTuple, Optional
from enum import IntEnum

from .expr import Var, Expr
from .interval import Interval
from .types import Real
from .linExpr import evalOp, displayLinExprHelper, FLIP_OP, IneqMode, parseAffine, parseLinCmpExpr

DEFAULT_BOUND = Interval(0, None, True, False)
DEFAULT_TOL = 1e-8


class ScipyLinprogInput(NamedTuple):
    c: Any
    A_ub: Any
    b_ub: Any
    A_eq: Any
    b_eq: Any
    bounds: Sequence[tuple[Optional[float], Optional[float]]]


class LpStatus(IntEnum):
    success = 0
    ile = 0
    infeasible = 0
    unbounded = 0
    numDiff = 0


class LinProgOutput(NamedTuple):
    status: LpStatus
    message: str
    optSol: Any = None
    optVal: Optional[float] = None
    slack: Any = None
    nIter: int = 0


def toFloatPair(interval: Interval, tol: float = DEFAULT_TOL) -> tuple[Optional[float], Optional[float]]:
    beg: Optional[float] = None
    end: Optional[float] = None
    if interval.beg is not None:
        beg = float(interval.beg)
        if not interval.begClosed:
            beg += tol
    if interval.end is not None:
        end = float(interval.end)
        if not interval.endClosed:
            end -= tol
    return (beg, end)


def flattenVarsHelper(a: object, varNames: MutableSequence[object],
        varNameToIndex: MutableMapping[object, int],
        varBounds: MutableSequence[Optional[Interval]]) -> None:
    if isinstance(a, str) or isinstance(a, Var):
        varName: object
        if isinstance(a, Var):
            varName = a.name
        else:
            varName = a
        if varName not in varNameToIndex:
            varNames.append(varName)
            varBounds.append(None)
            varNameToIndex[varName] = len(varNameToIndex)
    elif isinstance(a, Sequence):
        for x in a:
            flattenVarsHelper(x, varNames, varNameToIndex, varBounds)
    elif isinstance(a, Mapping):
        for varName, interval in a.items():
            varIndex = varNameToIndex.get(varName)
            if varIndex is None:
                varNames.append(varName)
                varBounds.append(interval)
                varNameToIndex[varName] = len(varNameToIndex)
            else:
                bound = varBounds[varIndex]
                if bound is None:
                    varBounds[varIndex] = interval
                elif bound.equals(interval):
                    raise ValueError(f'variable {varName} got multiple distinct bounds')
    else:
        raise TypeError(f'got {type(a)} in flattenVarsHelper')


class LinProg:
    def __init__(self, objType: Literal['min', 'max'], vars: object, objective: object,
            defaultBound: Interval = DEFAULT_BOUND):
        varNames: list[object] = []
        varNameToIndex: dict[object, int] = {}
        varBounds: list[Optional[Interval]] = []
        flattenVarsHelper(vars, varNames, varNameToIndex, varBounds)
        self.varNames: Sequence[object] = varNames
        self.varNameToIndex: Mapping[object, int] = varNameToIndex
        self.varBounds: Sequence[Interval] = [defaultBound if bound is None else bound for bound in varBounds]

        self.objType = objType
        objCoeffsMap, self.objConst = parseAffine(objective)
        self.objVec = [objCoeffsMap.get(varName, 0) for varName in varNames]

        self.hasFalse = False
        self.ubNameList: list[Optional[str]] = []
        self.aUbList: list[Sequence[Real]] = []
        self.bUbList: list[Real] = []
        self.isStrictList: list[bool] = []
        self.eqNameList: list[Optional[str]] = []
        self.aEqList: list[Sequence[Real]] = []
        self.bEqList: list[Real] = []

    def addConstraint(self, coeffs: Collection[tuple[object, Real]], op: str, rhs: Real,
            name: Optional[str] = None) -> None:
        assert op in ('==', '≤', '<', '≥', '>')
        if len(coeffs) == 0:
            if not evalOp(0, op, rhs):
                self.hasFalse = True
            return
        a: list[Real] = [0] * len(self.varNames)
        negate = (op in ('≥', '>'))
        for varName, coeff in coeffs:
            index = self.varNameToIndex[varName]
            a[index] = -coeff if negate else coeff
        if negate:
            op, rhs = FLIP_OP[op], -rhs
        if op == '==':
            self.aEqList.append(a)
            self.bEqList.append(rhs)
            self.eqNameList.append(name)
        else:
            self.aUbList.append(a)
            self.bUbList.append(rhs)
            self.ubNameList.append(name)
            self.isStrictList.append(op == '<')

    def addConstraintExpr(self, expr: Expr | bool, name: Optional[str] = None) -> None:
        if isinstance(expr, bool):
            if expr is False:
                self.hasFalse = True
            return
        linExpr = parseLinCmpExpr(expr, IneqMode.exact)
        self.addConstraint(linExpr.coeffMap.items(), linExpr.op, linExpr.rhs, name=name)

    def addDoubleConstraint(self, coeffs: Collection[tuple[object, Real]], interval: Interval,
            name: Optional[str] = None) -> None:
        if interval.isEmpty():
            self.hasFalse = True
        elif interval.beg == interval.end:
            if interval.beg is not None:
                self.addConstraint(coeffs, '==', interval.beg, name=name)
        else:
            if interval.beg is not None:
                newName = name + '.lb' if name is not None else None
                self.addConstraint(coeffs, '≥' if interval.begClosed else '>', interval.beg, name=newName)
            if interval.end is not None:
                newName = name + '.ub' if name is not None else None
                self.addConstraint(coeffs, '≤' if interval.endClosed else '<', interval.end, name=newName)

    def addDoubleConstraints(self, constrs: Iterable[tuple[Collection[tuple[object, Real]], Interval]]) -> None:
        # can accept a ConstrMap.items()
        for coeffs, interval in constrs:
            self.addDoubleConstraint(coeffs, interval)

    def __str__(self) -> str:
        lines: list[str] = []
        lineParts: list[str] = [self.objType]
        displayLinExprHelper(zip(self.varNames, self.objVec), lineParts)
        lines.append(' '.join(lineParts))

        for constrName, a, b in zip(self.eqNameList, self.aEqList, self.bEqList):
            lineParts.clear()
            if constrName is not None:
                lineParts.append(constrName + ':')
            displayLinExprHelper(zip(self.varNames, a), lineParts)
            lineParts.append('==')
            lineParts.append(str(b))
            lines.append(' '.join(lineParts))
        for constrName, a, b, isStrict in zip(self.ubNameList, self.aUbList, self.bUbList, self.isStrictList):
            lineParts.clear()
            if constrName is not None:
                lineParts.append(constrName + ':')
            displayLinExprHelper(zip(self.varNames, a), lineParts)
            lineParts.append('<' if isStrict else '≤')
            lineParts.append(str(b))
            lines.append(' '.join(lineParts))
        for varName, bound in zip(self.varNames, self.varBounds):
            lines.append(' '.join([str(varName), '∈', str(bound)]))
        lines.append('.')
        return '\n'.join(lines)

    def getScipyInput(self, tol: float = DEFAULT_TOL) -> Optional[ScipyLinprogInput]:
        if self.hasFalse:
            return None
        import numpy as np
        c = np.array(self.objVec, dtype=float)
        if self.objType == 'max':
            c = -c
        d = len(self.varNames)
        A_ub = np.array(self.aUbList, dtype=float)
        if not self.aUbList:
            A_ub = A_ub.reshape((0, d))
        A_eq = np.array(self.aEqList, dtype=float)
        if not self.aEqList:
            A_eq = A_eq.reshape((0, d))
        b_eq = np.array(self.bEqList, dtype=float)
        b_ub = np.array(self.bUbList, dtype=float) - tol * np.array(self.isStrictList)
        bounds = [toFloatPair(interval, tol) for interval in self.varBounds]
        return ScipyLinprogInput(c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)

    def solve(self, tol: float = DEFAULT_TOL) -> LinProgOutput:
        rawIn = self.getScipyInput(tol)
        if rawIn is None:
            return LinProgOutput(status=LpStatus.infeasible, message='LinProg.hasFalse is True')
        from scipy.optimize import linprog  # type: ignore[import]
        rawOut = linprog(c=rawIn.c, A_eq=rawIn.A_eq, b_eq=rawIn.b_eq, A_ub=rawIn.A_ub, b_ub=rawIn.b_ub,
            bounds=rawIn.bounds)
        outVal = rawOut.fun if self.objType == 'min' else -rawOut.fun
        return LinProgOutput(optSol=rawOut.x, optVal=outVal, slack=rawOut.slack,
            nIter=rawOut.nit, status=LpStatus(rawOut.status), message=rawOut.message)
