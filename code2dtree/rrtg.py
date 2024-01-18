from __future__ import annotations
from collections.abc import Callable
from typing import Optional

from .expr import Expr
from .node import Node, InternalNode, IfNode, FrozenIfNode, ReturnNode


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


class FuncArgs:
    def __init__(self, *args: object, **kwargs: object):
        self.args = args
        self.kwargs = kwargs


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

    def runOnce(self, func: Callable[..., object], funcArgs: FuncArgs) -> None:
        Expr.globalTreeGen = self
        result = func(*(funcArgs.args), **(funcArgs.kwargs))
        self.reportEnd(result)
        Expr.globalTreeGen = None

    def run(self, func: Callable[..., object], funcArgs: FuncArgs) -> None:
        Expr.globalTreeGen = self
        while not self.finished():
            result = func(*(funcArgs.args), **(funcArgs.kwargs))
            self.reportEnd(result)
        Expr.globalTreeGen = None


def func2dtree(func: Callable[..., object], funcArgs: FuncArgs, treeExplorer: Optional[TreeExplorer] = None) -> Node:
    if treeExplorer is None:
        treeExplorer = CachedTreeExplorer()
    gen = RepeatedRunTreeGen(treeExplorer)
    gen.run(func, funcArgs)
    assert gen.root is not None
    return gen.root
