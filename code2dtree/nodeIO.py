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
from .htmlGen import HtmlWriter
from .types import JsonVal


PKG_DIR = os.path.dirname(os.path.abspath(__file__))


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
    elif ext == '.html':
        with open(fpath, 'w') as fp:
            options = HtmlOptions(file=fp)
            dtreeToHtml(dtree, options)
    else:
        raise ValueError('unsupported output extension ' + ext)


HtmlOptions = PrintOptions
DEFAULT_HO = HtmlOptions()


@dataclasses.dataclass
class HtmlPrintStatus:
    writer: HtmlWriter
    nodes: int = 0
    leaves: int = 0


def dtreeToHtmlHelper(node: Optional[Node], options: HtmlOptions, status: HtmlPrintStatus) -> None:
    writer = status.writer
    nodeId = status.nodes
    status.nodes += 1
    defaultAttrMap = {'id': 'node' + str(nodeId)}
    checkBoxAttrMap = {'type': 'checkbox', 'name': 'node' + str(nodeId)}
    if node is None:
        with writer.tag('div', defaultAttrMap | {'class': 'node unfinNode'}):
            writer.addScTag('input', checkBoxAttrMap)
            writer.addTag('span', IfNode.noneString)
    elif isinstance(node, LeafNode):
        with writer.tag('div', defaultAttrMap | {'class': 'node leafNode'}):
            writer.addScTag('input', checkBoxAttrMap)
            writer.addTag('span', node.getLabel())
            status.leaves += 1
    elif isinstance(node, IfNode):
        with writer.tag('details', defaultAttrMap | {'class': 'node ifNode'}):
            with writer.tag('summary'):
                writer.addScTag('input', checkBoxAttrMap)
                writer.addTag('span', node.getLabel(options.simplify) + ':')
            with writer.tag('div', {'class': 'nodeFrag ifTrue'}):
                dtreeToHtmlHelper(node.kids[1], options, status)
            writer.addTag('div', 'else:', {'class': 'nodeElse'})
            with writer.tag('div', {'class': 'nodeFrag ifFalse'}):
                dtreeToHtmlHelper(node.kids[0], options, status)
    elif isinstance(node, FrozenIfNode):
        if options.showFrozenIf or node.kids[0] is None:
            with writer.tag('div', defaultAttrMap | {'class': 'node frozenIfNode'}):
                writer.addScTag('input', checkBoxAttrMap)
                writer.addTag('span', node.getLabel(options.simplify))
        dtreeToHtmlHelper(node.kids[0], options, status)
    elif isinstance(node, InfoNode):
        with writer.tag('div', defaultAttrMap | {'class': 'node infoNode'}):
            writer.addScTag('input', checkBoxAttrMap)
            writer.addTag('span', node.getLabel())
        dtreeToHtmlHelper(node.kids[0], options, status)
    else:
        raise ValueError('unsupported node type ' + type(node).__name__)


HTML_TEMPLATE = ("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="color-scheme" content="dark light" />
<style>""",

"""</style>
<script>""",

"""</script>
</head>
<body>
""",

"""</body>
</html>""")


def dtreeToHtml(node: Node, options: HtmlOptions) -> None:
    print(HTML_TEMPLATE[0], file=options.file)
    with open(os.path.join(PKG_DIR, 'style.css')) as fp:
        options.file.write(fp.read())
    print(HTML_TEMPLATE[1], file=options.file)
    with open(os.path.join(PKG_DIR, 'dtree.js')) as fp:
        options.file.write(fp.read())
    options.file.write(HTML_TEMPLATE[2])

    writer = HtmlWriter(options.file, options.indentStr)
    status = HtmlPrintStatus(writer=writer)
    with writer.tag('div', {'class': 'dtree'}):
        dtreeToHtmlHelper(node, options, status)
    print(HTML_TEMPLATE[3], file=options.file)
