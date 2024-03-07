from __future__ import annotations
import sys
import dataclasses
from collections.abc import Iterable, MutableSequence, Sequence
from typing import Any, Optional, TextIO, NamedTuple

from .expr import Expr, prettyExprRepr
from .terminal import termPrint, TermColorOptions
from .types import JsonVal


class PrintOptions(NamedTuple):
    simplify: bool = False
    showFrozenIf: bool = True
    indentStr: str = '  '
    file: TextIO = sys.stdout
    lineNoCols: int = 0
    marginCols: int = 0


@dataclasses.dataclass
class PrintStatus:
    nodes: int = 0
    leaves: int = 0
    lines: int = 0
    indent: int = 0


@dataclasses.dataclass
class PrintAttr:
    visible: bool = True
    margin: str = ''
    termColorOpts: Optional[TermColorOptions] = None


DEFAULT_PO = PrintOptions()


def getPrefix(attr: PrintAttr, options: PrintOptions, status: PrintStatus) -> str:
    parts = []
    if options.lineNoCols:
        parts.append(str(status.lines).rjust(options.lineNoCols))
        parts.append('|')
    if options.marginCols:
        parts.append(attr.margin.rjust(options.marginCols))
        parts.append('|')
    parts.append(status.indent * options.indentStr)
    return ''.join(parts)


class Node:
    noneString = '(unfinished)'
    passString = 'pass'

    def __init__(self, expr: object, parent: Optional[InternalNode], explored: bool):
        self.expr = expr
        self.parent = parent
        self.explored = explored
        self.printAttr: PrintAttr = PrintAttr()
        self.userData: dict[Any, Any] = {}

    def __repr__(self) -> str:
        return '{}({}, exp={})'.format(self.__class__.__name__, self.expr, self.explored)

    def print(self, options: PrintOptions = DEFAULT_PO, status: Optional[PrintStatus] = None) -> None:
        if self.printAttr.visible:
            raise NotImplementedError()

    def getKids(self) -> Sequence[Optional[Node]]:
        raise NotImplementedError()

    def getLabel(self) -> str:
        raise NotImplementedError()

    def getLeaves(self) -> Iterable[LeafNode]:
        raise NotImplementedError()

    def goDown(self, path: Iterable[int]) -> Optional[Node]:
        node: Optional[Node] = self
        for index in path:
            if node is None:
                raise IndexError('cannot index None')
            kids = node.getKids()
            if len(kids) <= index:
                raise IndexError(f'not enough kids at {node}')
            else:
                node = kids[index]
        return node

    def toIsolatedJson(self) -> dict[str, JsonVal]:
        # isolated means that information about parents and kids is absent
        return {
            'type': type(self).__name__,
            'expr': prettyExprRepr(self.expr),
            'explored': self.explored,
            'printAttr': dataclasses.asdict(self.printAttr),
            'userData': self.userData,
        }


class LeafNode(Node):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent, True)
        self.explorerOutput: object = None

    def getKids(self) -> Sequence[None]:
        return ()

    def getLeaves(self) -> Iterable[LeafNode]:
        yield self


class ReturnNode(LeafNode):
    def __init__(self, expr: object, parent: Optional[InternalNode]):
        super().__init__(expr, parent)

    def getLabel(self) -> str:
        return 'return ' + prettyExprRepr(self.expr)

    def print(self, options: PrintOptions = DEFAULT_PO, status: Optional[PrintStatus] = None) -> None:
        if not self.printAttr.visible:
            return
        if status is None:
            status = PrintStatus()
        termPrint(getPrefix(self.printAttr, options, status) + self.getLabel(),
            options=self.printAttr.termColorOpts, file=options.file)
        status.leaves += 1
        status.nodes += 1
        status.lines += 1


class InternalNode(Node):
    def __init__(self, expr: object, parent: Optional[InternalNode], nKids: int):
        super().__init__(expr, parent, False)
        self.kids: MutableSequence[Optional[Node]] = [None] * nKids

    def getKids(self) -> Sequence[Optional[Node]]:
        return self.kids

    def getLeaves(self) -> Iterable[LeafNode]:
        for kid in self.kids:
            if kid is None:
                print('getLeaves: found None node', file=sys.stderr)
            else:
                yield from kid.getLeaves()

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

    def toIsolatedJson(self) -> dict[str, JsonVal]:
        d = super().toIsolatedJson()
        d['nKids'] = len(self.kids)
        return d


class DecisionNode(InternalNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode], nKids: int):
        super().__init__(expr, parent, nKids)
        self.sexpr: Optional[Expr] = None  # simplified expr

    def toIsolatedJson(self) -> dict[str, JsonVal]:
        d = super().toIsolatedJson()
        d['sexpr'] = prettyExprRepr(self.sexpr)
        return d


class IfNode(DecisionNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode]):
        super().__init__(expr, parent, 2)

    def getLabel(self, simplify: bool = False) -> str:
        expr = self.sexpr if simplify else self.expr
        return 'if ' + prettyExprRepr(expr)

    def print(self, options: PrintOptions = DEFAULT_PO, status: Optional[PrintStatus] = None) -> None:
        if not self.printAttr.visible:
            return
        if status is None:
            status = PrintStatus()
        termPrint(getPrefix(self.printAttr, options, status) + self.getLabel(options.simplify) + ':',
            options=self.printAttr.termColorOpts, file=options.file)
        status.lines += 1
        status.nodes += 1
        status.indent += 1
        if self.kids[1] is None:
            termPrint(getPrefix(self.printAttr, options, status) + Node.noneString,
                options=self.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        elif self.kids[1].printAttr.visible:
            self.kids[1].print(options, status)
        else:
            termPrint(getPrefix(self.printAttr, options, status) + Node.passString,
                options=self.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        status.indent -= 1
        termPrint(getPrefix(self.printAttr, options, status) + 'else:',
            options=self.printAttr.termColorOpts, file=options.file)
        status.lines += 1
        status.indent += 1
        if self.kids[0] is None:
            termPrint(getPrefix(self.printAttr, options, status) + Node.noneString,
                options=self.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        elif self.kids[0].printAttr.visible:
            self.kids[0].print(options, status)
        else:
            termPrint(getPrefix(self.printAttr, options, status) + Node.passString,
                options=self.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        status.indent -= 1


class FrozenIfNode(DecisionNode):
    def __init__(self, expr: Expr, parent: Optional[InternalNode], b: bool):
        super().__init__(expr, parent, 1)
        self.b = b

    def toIsolatedJson(self) -> dict[str, JsonVal]:
        d = super().toIsolatedJson()
        d['b'] = self.b
        return d

    def getLabel(self, simplify: bool = False) -> str:
        expr = self.sexpr if simplify else self.expr
        return (('assert ' if self.kids[0] is not None else 'asserting ')
            + ('' if self.b else 'not(') + prettyExprRepr(expr) + ('' if self.b else ')'))

    def print(self, options: PrintOptions = DEFAULT_PO, status: Optional[PrintStatus] = None) -> None:
        if not self.printAttr.visible:
            return
        if status is None:
            status = PrintStatus()
        if options.showFrozenIf or self.kids[0] is None:
            termPrint(getPrefix(self.printAttr, options, status) + self.getLabel(options.simplify),
                options=self.printAttr.termColorOpts, file=options.file)
            status.nodes += 1
            status.lines += 1
        if self.kids[0] is None:
            status.indent += 1
            termPrint(Node.noneString, options=self.printAttr.termColorOpts, file=options.file)
            status.lines += 1
            status.indent -= 1
        else:
            self.kids[0].print(options, status)


class InfoNode(InternalNode):
    def __init__(self, value: object, parent: Optional[InternalNode], verb: str):
        super().__init__(value, parent, 1)
        self.verb = verb

    def toIsolatedJson(self) -> dict[str, JsonVal]:
        d = super().toIsolatedJson()
        d['verb'] = self.verb
        return d

    @classmethod
    def get(cls, value: object, parent: Optional[InternalNode], verb: str) -> InfoNode:
        if verb == YieldNode.defaultVerb:
            return YieldNode(value, parent)
        elif verb == CheckpointNode.defaultVerb:
            return CheckpointNode(value, parent)
        else:
            return InfoNode(value, parent, verb)

    def getLabel(self) -> str:
        return self.verb + ' ' + prettyExprRepr(self.expr)

    def print(self, options: PrintOptions = DEFAULT_PO, status: Optional[PrintStatus] = None) -> None:
        if status is None:
            status = PrintStatus()
        if self.printAttr.visible:
            termPrint(getPrefix(self.printAttr, options, status) + self.getLabel(),
                options=self.printAttr.termColorOpts, file=options.file)
            status.nodes += 1
            status.lines += 1
        if self.kids[0] is None:
            termPrint(getPrefix(self.printAttr, options, status) + Node.noneString,
                options=self.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        else:
            self.kids[0].print(options, status)


class CheckpointNode(InfoNode):
    defaultVerb = 'print:'

    def __init__(self, value: object, parent: Optional[InternalNode]):
        super().__init__(value, parent, CheckpointNode.defaultVerb)


class YieldNode(InfoNode):
    defaultVerb = 'yield'

    def __init__(self, value: object, parent: Optional[InternalNode]):
        super().__init__(value, parent, YieldNode.defaultVerb)


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


def dtreeToFlatJson(root: Optional[Node]) -> dict[str, JsonVal]:
    nodeJsons: list[Optional[JsonVal]] = []
    parentOf: list[Optional[int]] = []
    output: dict[str, JsonVal] = {'parent': parentOf, 'nodes': nodeJsons}
    if root is None:
        print('Warning: empty tree passed to dtreeToJson', file=sys.stderr)

    def explore(node: Optional[Node], parentId: Optional[int]) -> Optional[int]:
        nodeId = len(nodeJsons)
        parentOf.append(parentId)
        if node is None:
            nodeJsons.append(None)
            return None
        else:
            nodeJson = node.toIsolatedJson()
            nodeJsons.append(nodeJson)
            nodeJson['parentId'] = parentId
            kidIds: list[Optional[int]] = []
            nodeJson['kidIds'] = kidIds
            for kid in node.getKids():
                kidId = explore(kid, nodeId)
                kidIds.append(kidId)
            return nodeId

    explore(root, None)
    return output


def printGraphViz(root: Optional[Node], file: TextIO) -> None:
    if root is None:
        print('Warning: empty tree passed to printGraphViz', file=sys.stderr)
    else:
        V, E = toVE(root)
        print('digraph DTree{', file=file)
        for i, w in enumerate(V):
            print('v{} [label="{}"];'.format(i, w.getLabel()), file=file)
        for (u, v, label) in E:
            if label is None:
                print(f'v{u} -> v{v};', file=file)
            else:
                print(f'v{u} -> v{v} [label="{label}"];', file=file)
        print('}', file=file)
