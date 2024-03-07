from __future__ import annotations
import sys
import dataclasses
from collections.abc import Iterable, MutableSequence, Sequence
from typing import Any, Optional

from .expr import Expr, prettyExprRepr
from .terminal import TermColorOptions
from .types import JsonVal


@dataclasses.dataclass
class PrintAttr:
    visible: bool = True
    margin: str = ''
    termColorOpts: Optional[TermColorOptions] = None


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


class CheckpointNode(InfoNode):
    defaultVerb = 'print:'

    def __init__(self, value: object, parent: Optional[InternalNode]):
        super().__init__(value, parent, CheckpointNode.defaultVerb)


class YieldNode(InfoNode):
    defaultVerb = 'yield'

    def __init__(self, value: object, parent: Optional[InternalNode]):
        super().__init__(value, parent, YieldNode.defaultVerb)
