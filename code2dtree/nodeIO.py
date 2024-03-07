from __future__ import annotations
import sys
import os.path
import json
import dataclasses
import subprocess
from typing import NamedTuple, Optional, TextIO

from .node import Node, LeafNode, InternalNode, IfNode, FrozenIfNode, InfoNode
from .node import PrintAttr
from .terminal import termPrint
from .types import JsonVal


class PrintOptions(NamedTuple):
    simplify: bool = False
    showFrozenIf: bool = True
    indentStr: str = '  '
    file: TextIO = sys.stdout
    lineNoCols: int = 0
    marginCols: int = 0


DEFAULT_PO = PrintOptions()


@dataclasses.dataclass
class PrintStatus:
    nodes: int = 0
    leaves: int = 0
    lines: int = 0
    indent: int = 0


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


def printTree(node: Node, options: PrintOptions = DEFAULT_PO, status: Optional[PrintStatus] = None) -> None:
    if status is None:
        status = PrintStatus()
    if isinstance(node, LeafNode):
        if not node.printAttr.visible:
            return
        termPrint(getPrefix(node.printAttr, options, status) + node.getLabel(),
            options=node.printAttr.termColorOpts, file=options.file)
        status.leaves += 1
        status.nodes += 1
        status.lines += 1
    elif isinstance(node, IfNode):
        if not node.printAttr.visible:
            return
        termPrint(getPrefix(node.printAttr, options, status) + node.getLabel(options.simplify) + ':',
            options=node.printAttr.termColorOpts, file=options.file)
        status.lines += 1
        status.nodes += 1
        status.indent += 1
        if node.kids[1] is None:
            termPrint(getPrefix(node.printAttr, options, status) + Node.noneString,
                options=node.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        elif node.kids[1].printAttr.visible:
            printTree(node.kids[1], options, status)
        else:
            termPrint(getPrefix(node.printAttr, options, status) + Node.passString,
                options=node.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        status.indent -= 1
        termPrint(getPrefix(node.printAttr, options, status) + 'else:',
            options=node.printAttr.termColorOpts, file=options.file)
        status.lines += 1
        status.indent += 1
        if node.kids[0] is None:
            termPrint(getPrefix(node.printAttr, options, status) + Node.noneString,
                options=node.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        elif node.kids[0].printAttr.visible:
            printTree(node.kids[0], options, status)
        else:
            termPrint(getPrefix(node.printAttr, options, status) + Node.passString,
                options=node.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        status.indent -= 1
    elif isinstance(node, FrozenIfNode):
        if not node.printAttr.visible:
            return
        if options.showFrozenIf or node.kids[0] is None:
            termPrint(getPrefix(node.printAttr, options, status) + node.getLabel(options.simplify),
                options=node.printAttr.termColorOpts, file=options.file)
            status.nodes += 1
            status.lines += 1
        if node.kids[0] is None:
            status.indent += 1
            termPrint(Node.noneString, options=node.printAttr.termColorOpts, file=options.file)
            status.lines += 1
            status.indent -= 1
        else:
            printTree(node.kids[0], options, status)
    elif isinstance(node, InfoNode):
        if node.printAttr.visible:
            termPrint(getPrefix(node.printAttr, options, status) + node.getLabel(),
                options=node.printAttr.termColorOpts, file=options.file)
            status.nodes += 1
            status.lines += 1
        if node.kids[0] is None:
            termPrint(getPrefix(node.printAttr, options, status) + Node.noneString,
                options=node.printAttr.termColorOpts, file=options.file)
            status.lines += 1
        else:
            printTree(node.kids[0], options, status)


GraphEdge = tuple[int, int, Optional[int]]


def toVE(root: Node) -> tuple[list[Node], list[GraphEdge]]:
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
                E.append((ui, vi, None))
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

    explore(root, 0)
    return (V, E)


def dtreeToFlatJson(root: Node) -> dict[str, JsonVal]:
    nodeJsons: list[Optional[JsonVal]] = []
    parentOf: list[Optional[int]] = []
    output: dict[str, JsonVal] = {'parent': parentOf, 'nodes': nodeJsons}

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


def printGraphViz(root: Node, file: TextIO) -> None:
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


SAVE_FORMATS = ('txt', 'dot', 'svg', 'json')


def saveTree(dtree: Node, fpath: str) -> None:
    basePath, ext = os.path.splitext(fpath)
    if ext == '.txt':
        with open(fpath, 'w') as fp:
            options = PrintOptions(file=fp, lineNoCols=3, marginCols=3)
            printTree(dtree, options)
    elif ext == '.dot':
        with open(fpath, 'w') as fp:
            printGraphViz(dtree, fp)
    elif ext == '.svg':
        dotPath = basePath + '.dot'
        with open(dotPath, 'w') as fp:
            printGraphViz(dtree, fp)
        subprocess.run(['dot', '-T', 'svg', dotPath, '-o', fpath], check=True)
    elif ext == '.json':
        jsonObj = dtreeToFlatJson(dtree)
        with open(fpath, 'w') as fp:
            json.dump(jsonObj, fp, indent=4)
    else:
        raise ValueError('unsupported output extension ' + ext)
