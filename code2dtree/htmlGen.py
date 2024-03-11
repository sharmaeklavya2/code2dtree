from __future__ import annotations
from collections.abc import Mapping, MutableSequence
from typing import Optional, Self, TextIO


AttrT = Optional[Mapping[str, str]]

textEscapeTable = str.maketrans({'&': '&amp;', '<': '&lt;', '>': '&gt;'})
attrValEscapeTable = textEscapeTable | str.maketrans({'"': '&quot;', "'": '&apos;'})


def getTagHelper(name: str, parts: MutableSequence[str], attrMap: AttrT = None,
        selfClosing: bool = False) -> None:
    # security: don't put untrusted content in name or fields.keys
    parts.extend(['<', name])
    if attrMap is not None:
        for attr, val in attrMap.items():
            parts.extend([' ', attr, '="', val.translate(attrValEscapeTable), '"'])
    if selfClosing:
        parts.append('/')
    parts.append('>')


def getTag(name: str, attrMap: AttrT = None, selfClosing: bool = False) -> str:
    # security: don't put untrusted content in name or fields.keys
    parts: list[str] = []
    getTagHelper(name, parts, attrMap, selfClosing)
    return ''.join(parts)


class TagCtxMgr:
    def __init__(self, writer: HtmlWriter, tagName: str, attrMap: AttrT = None):
        self.writer = writer
        self.tagName = tagName
        self.attrMap = attrMap

    def __enter__(self) -> Self:
        self.writer.openTag(self.tagName, self.attrMap)
        return self

    def __exit__(self, exc_type: object = None, exc_value: object = None, traceback: object = None) -> None:
        self.writer.closeTag(self.tagName)


class HtmlWriter:
    def __init__(self, file: TextIO, indentStr: str, indentLevel: int = 0):
        self.file = file
        self.indentStr = indentStr
        self.indent = indentLevel
        self.lines = 0

    def openTag(self, name: str, attrMap: AttrT = None) -> None:
        parts = [self.indent * self.indentStr]
        getTagHelper(name, parts, attrMap)
        print(''.join(parts), file=self.file)
        self.indent += 1
        self.lines += 1

    def closeTag(self, name: str) -> None:
        self.indent -= 1
        parts = [self.indent * self.indentStr, '</', name, '>']
        print(''.join(parts), file=self.file)
        self.lines += 1

    def addTag(self, name: str, text: str, attrMap: AttrT = None) -> None:
        parts = [self.indent * self.indentStr]
        getTagHelper(name, parts, attrMap)
        parts.append(text.translate(textEscapeTable))
        parts.extend(['</', name, '>'])
        print(''.join(parts), file=self.file)
        self.lines += 1

    def addScTag(self, name: str, attrMap: AttrT = None) -> None:
        parts = [self.indent * self.indentStr]
        getTagHelper(name, parts, attrMap, selfClosing=True)
        print(''.join(parts), file=self.file)
        self.lines += 1

    def tag(self, name: str, attrMap: AttrT = None) -> TagCtxMgr:
        return TagCtxMgr(self, name, attrMap)
