from __future__ import annotations
from collections.abc import Callable, Generator, Sequence
from typing import Optional, TextIO, Union

from .expr import Expr
from .treeExplorer import TreeExplorer, CachedTreeExplorer
from .node import Node, InternalNode, ReturnNode
from .node import DecisionNode, IfNode, FrozenIfNode
from .node import InfoNode, CheckpointNode, YieldNode


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

    def createAndGoDown(self, node: InternalNode, i: int) -> None:
        assert self.current is None
        if self.parent is not None:
            assert self.kidIndex is not None
            self.parent.kids[self.kidIndex] = node
        else:
            self.root = node
        self.parent = node
        self.current = None
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
        b, checkOther, sexpr = self.explorer.decideIf(expr)
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
                node: DecisionNode = IfNode(expr, self.parent)
            else:
                node = FrozenIfNode(expr, self.parent, b)
            node.sexpr = sexpr
            self.createAndGoDown(node, b if checkOther else 0)
            return b

    def addInfo(self, v: object, verb: str) -> None:
        if self.current is not None:
            assert isinstance(self.current, InfoNode) and self.current.verb == verb
            self.goDown(0)
        else:
            node = InfoNode.get(v, self.parent, verb)
            self.createAndGoDown(node, 0)

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
        node.explorerOutput = self.explorer.noteReturn(expr)

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

    def iterateOnce(self, gen: Generator[object, None, object]) -> None:
        Expr.globalTreeGen = self
        try:
            while True:
                yVal = next(gen)
                self.addInfo(yVal, YieldNode.defaultVerb)
        except StopIteration as e:
            self.reportEnd(e.value)
        Expr.globalTreeGen = None


def func2dtree(func: Callable[..., object], funcArgs: Union[FuncArgs, Sequence[object]],
        treeExplorer: Optional[TreeExplorer] = None) -> Node:
    if treeExplorer is None:
        treeExplorer = CachedTreeExplorer()
    if isinstance(funcArgs, FuncArgs):
        fa = funcArgs
    else:
        fa = FuncArgs(*funcArgs)
    gen = RepeatedRunTreeGen(treeExplorer)
    gen.run(func, fa)
    assert gen.root is not None
    return gen.root


def genFunc2dtree(func: Callable[..., Generator[object, None, object]], funcArgs: Union[FuncArgs, Sequence[object]],
        treeExplorer: Optional[TreeExplorer] = None) -> Node:
    if treeExplorer is None:
        treeExplorer = CachedTreeExplorer()
    if isinstance(funcArgs, FuncArgs):
        fa = funcArgs
    else:
        fa = FuncArgs(*funcArgs)
    treeGen = RepeatedRunTreeGen(treeExplorer)
    while not treeGen.finished():
        g = func(*(fa.args), **(fa.kwargs))
        treeGen.iterateOnce(g)
    assert treeGen.root is not None
    return treeGen.root


def checkpoint(v: object, checkConsistency: bool = False, fp: Optional[TextIO] = None) -> None:
    if Expr.globalTreeGen is None:
        if fp is not None:
            print(v, file=fp)
    else:
        Expr.globalTreeGen.addInfo(v, CheckpointNode.defaultVerb)
