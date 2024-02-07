from __future__ import annotations
import sys
from collections.abc import Iterable, MutableSequence
from typing import Optional, TextIO, NamedTuple

from .expr import Expr, prettyExprRepr


class PrintOptions(NamedTuple):
    simplify: bool = False
    frozenIf: bool = True
    indentStr: str = '  '
    file: TextIO = sys.stdout


DEFAULT_PO = PrintOptions()


class Node:
    def __init__(self, expr: object, parent: Optional[InternalNode], explored: bool):
        self.expr = expr
        self.parent = parent
        self.explored = explored

    def __repr__(self) -> str:
        return '{}({}, exp={})'.format(self.__class__.__name__, self.expr, self.explored)

    def print(self, options: PrintOptions = DEFAULT_PO, indent: int = 0) -> None:
        raise NotImplementedError()


class LeafNode(Node):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent, True)


class ReturnNode(LeafNode):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent)

    def print(self, options: PrintOptions = DEFAULT_PO, indent: int = 0) -> None:
        print(options.indentStr * indent + 'return ' + prettyExprRepr(self.expr), file=options.file)


class NothingNode(LeafNode):
    def __init__(self, parent: Optional[InternalNode]):
        super().__init__(None, parent)

    def print(self, options: PrintOptions = DEFAULT_PO, indent: int = 0) -> None:
        print(options.indentStr * indent + '(nothing)', file=options.file)


class InternalNode(Node):
    def __init__(self, expr: object, parent: Optional[InternalNode], nKids: int):
        super().__init__(expr, parent, False)
        self.kids: MutableSequence[Optional[Node]] = [None] * nKids

    def getKidsExploreStatus(self) -> tuple[int, int]:
        nEKids, nKids = 0, 0
        for kid in self.kids:
            nKids += 1
            nEKids += kid is not None and kid.explored
        return (nEKids, nKids)

    def setExploreStatusRec(self) -> None:
        nEKids, nKids = self.getKidsExploreStatus()
        if nEKids == nKids:
            self.explored = True
            if self.parent is not None:
                self.parent.setExploreStatusRec()

    def __repr__(self) -> str:
        parts = ['{}({}'.format(self.__class__.__name__, self.expr)]
        for i, kid in enumerate(self.kids):
            parts.append('{}={}'.format(i, kid))
        return ', '.join(parts) + ')'


class DecisionNode(InternalNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode], nKids: int):
        super().__init__(expr, parent, nKids)
        self.sexpr: Optional[Expr] = None  # simplified expr


class IfNode(DecisionNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode]):
        super().__init__(expr, parent, 2)

    def print(self, options: PrintOptions = DEFAULT_PO, indent: int = 0) -> None:
        noneString = options.indentStr * (indent + 1) + '(unfinished)'
        expr = self.sexpr if options.simplify else self.expr
        print(options.indentStr * indent + 'if ' + prettyExprRepr(expr) + ':', file=options.file)
        if self.kids[1] is None:
            print(noneString, file=options.file)
        else:
            self.kids[1].print(options, indent+1)
        print(options.indentStr * indent + 'else:', file=options.file)
        if self.kids[0] is None:
            print(noneString, file=options.file)
        else:
            self.kids[0].print(options, indent+1)


class FrozenIfNode(DecisionNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode], b: bool):
        super().__init__(expr, parent, 1)
        self.b = b

    def print(self, options: PrintOptions = DEFAULT_PO, indent: int = 0) -> None:
        noneString = options.indentStr * (indent + 1) + '(unfinished)'
        if options.frozenIf:
            expr = self.sexpr if options.simplify else self.expr
            print(options.indentStr * indent + 'assert ' + ('' if self.b else 'not(') +
                prettyExprRepr(expr) + ('' if self.b else ')'), file=options.file)
        if self.kids[0] is None:
            print(noneString, file=options.file)
        else:
            self.kids[0].print(options, indent)


class InfoNode(InternalNode):
    def __init__(self, value: object, parent: Optional[InternalNode], verb: str):
        super().__init__(value, parent, 1)
        self.verb = verb

    @classmethod
    def get(cls, value: object, parent: Optional[InternalNode], verb: str) -> InfoNode:
        if verb == YieldNode.defaultVerb:
            return YieldNode(value, parent)
        elif verb == CheckpointNode.defaultVerb:
            return CheckpointNode(value, parent)
        else:
            return InfoNode(value, parent, verb)

    def print(self, options: PrintOptions = DEFAULT_PO, indent: int = 0) -> None:
        noneString = options.indentStr * (indent + 1) + '(unfinished)'
        print(options.indentStr * indent + self.verb + ' ' + str(self.expr), file=options.file)
        if self.kids[0] is None:
            print(noneString, file=options.file)
        else:
            self.kids[0].print(options, indent)


class CheckpointNode(InfoNode):
    defaultVerb = 'print:'

    def __init__(self, value: object, parent: Optional[InternalNode]):
        super().__init__(value, parent, CheckpointNode.defaultVerb)


class YieldNode(InfoNode):
    defaultVerb = 'yield'

    def __init__(self, value: object, parent: Optional[InternalNode]):
        super().__init__(value, parent, YieldNode.defaultVerb)


def getLeaves(root: Optional[Node]) -> Iterable[LeafNode]:
    if root is None:
        print('getLeaves: found None node', file=sys.stderr)
    elif isinstance(root, LeafNode):
        yield root
    elif isinstance(root, InternalNode):
        for kid in root.kids:
            yield from getLeaves(kid)
    else:
        raise TypeError('getLeaves: root has type {}'.format(type(root).__name__))


GraphEdge = tuple[int, int, Optional[int]]


def toVE(root: Optional[Node]) -> tuple[list[Node], list[GraphEdge]]:
    V = []
    E: list[GraphEdge] = []
    id = 0

    def explore(u: Node, ui: int) -> None:
        nonlocal id
        V.append(u)
        if isinstance(u, IfNode):
            for j, v in enumerate(u.kids):
                if v is not None:
                    id += 1
                    vi = id
                    E.append((ui, vi, j))
                    explore(v, vi)
        elif isinstance(u, FrozenIfNode):
            j, v = 0, u.kids[0]
            if v is not None:
                id += 1
                vi = id
                E.append((ui, vi, int(u.b)))
                explore(v, vi)
        elif isinstance(u, InfoNode):
            v = u.kids[0]
            if v is not None:
                id += 1
                vi = id
                E.append((ui, vi, None))
                explore(v, vi)
        elif isinstance(u, InternalNode):
            raise TypeError('node type {} not supported'.format(repr(type(u).__name__)))

    if root is not None:
        explore(root, 0)
    else:
        print('Warning: empty tree passed to toVE', file=sys.stderr)
    return (V, E)


def printGraphViz(root: Optional[Node], file: TextIO) -> None:
    if root is None:
        print('Warning: empty tree passed to printGraphViz', file=sys.stderr)
    else:
        V, E = toVE(root)
        print('digraph DTree{', file=file)
        for i, w in enumerate(V):
            print('v{} [label="{}"];'.format(i, prettyExprRepr(w.expr)), file=file)
        for (u, v, label) in E:
            if label is None:
                print(f'v{u} -> v{v};', file=file)
            else:
                print(f'v{u} -> v{v} [label="{label}"];', file=file)
        print('}', file=file)
