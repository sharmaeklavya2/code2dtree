from .rrtg import RepeatedRunTreeGen
from typing import Mapping, Optional


class Expr:
    globalTreeGen: Optional[RepeatedRunTreeGen]
    def key(self) -> object: ...
    def __hash__(self) -> int: ...
    def __bool__(self) -> bool: ...

    def __pos__(self) -> Expr: ...
    def __neg__(self) -> Expr: ...
    def __abs__(self) -> UnExpr: ...
    def __round__(self) -> UnExpr: ...
    def __floor__(self) -> UnExpr: ...
    def __ceil__(self) -> UnExpr: ...

    def __add__(self, other: object) -> Expr: ...
    def __sub__(self, other: object) -> Expr: ...
    def __mul__(self, other: object) -> Expr: ...
    def __matmul__(self, other: object) -> BinExpr: ...
    def __truediv__(self, other: object) -> Expr: ...
    def __floordiv__(self, other: object) -> BinExpr: ...
    def __mod__(self, other: object) -> BinExpr: ...
    def __pow__(self, other: object) -> BinExpr: ...
    def __lshift__(self, other: object) -> BinExpr: ...
    def __rshift__(self, other: object) -> BinExpr: ...
    def __and__(self, other: object) -> BinExpr: ...
    def __or__(self, other: object) -> BinExpr: ...
    def __xor__(self, other: object) -> BinExpr: ...

    def __radd__(self, other: object) -> Expr: ...
    def __rsub__(self, other: object) -> Expr: ...
    def __rmul__(self, other: object) -> Expr: ...
    def __rmatmul__(self, other: object) -> BinExpr: ...
    def __rtruediv__(self, other: object) -> Expr: ...
    def __rfloordiv__(self, other: object) -> BinExpr: ...
    def __rmod__(self, other: object) -> BinExpr: ...
    def __rpow__(self, other: object) -> BinExpr: ...
    def __rlshift__(self, other: object) -> BinExpr: ...
    def __rrshift__(self, other: object) -> BinExpr: ...
    def __rand__(self, other: object) -> BinExpr: ...
    def __ror__(self, other: object) -> BinExpr: ...
    def __rxor__(self, other: object) -> BinExpr: ...

    def __lt__(self, other: object) -> BinExpr: ...
    def __le__(self, other: object) -> BinExpr: ...
    def __gt__(self, other: object) -> BinExpr: ...
    def __ge__(self, other: object) -> BinExpr: ...
    def __eq__(self, other: object) -> BinExpr: ...  # type: ignore[override]
    def __ne__(self, other: object) -> BinExpr: ...  # type: ignore[override]


class Var(Expr):
    @staticmethod
    def get(name: object) -> Var: ...
    name: object
    def __init__(self, name: object) -> None: ...


SUB_TR_TABLE: Mapping[int, Optional[int]]

def getVarList(listName: str, n: int, style: str = ...) -> list[Var]: ...


class BinExpr(Expr):
    op: str
    larg: object
    rarg: object
    def __init__(self, op: str, larg: object, rarg: object) -> None: ...


class UnExpr(Expr):
    op: str
    arg: object
    isFunc: bool
    def __init__(self, op: str, arg: object, isFunc: bool = ...) -> None: ...


BIN_OPS: Mapping[str, str]
UN_OPS: Mapping[str, str]
UN_FUNCS: Mapping[str, str]


def prettyExprRepr(x: object) -> str: ...
