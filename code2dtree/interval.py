from __future__ import annotations
from typing import Optional
from code2dtree.types import Real, strToReal

INFTY_STR = '∞'
NINFTY_STR = '-∞'


class Interval:
    def __init__(self, beg: Optional[Real], end: Optional[Real], begClosed: bool, endClosed: bool):
        # None means -infty or +infty
        self.beg = beg
        self.end = end
        self.begClosed = begClosed
        self.endClosed = endClosed

    @classmethod
    def fromStr(cls, s: str) -> Interval:
        if s[0] not in '([' or s[-1] not in ')]':
            raise ValueError('incorrect brackets')
        parts = s[1: -1].split(',')
        if len(parts) != 2:
            raise ValueError('string should have exactly 1 comma')
        return Interval(strToReal(parts[0]), strToReal(parts[1]), s[0] == '[', s[-1] == ']')

    def __str__(self) -> str:
        return ''.join((
            '[' if self.begClosed else '(',
            NINFTY_STR if self.beg is None else str(self.beg),
            ', ',
            INFTY_STR if self.end is None else str(self.end),
            ']' if self.endClosed else ')',
            ))

    def __repr__(self) -> str:
        return self.__class__.__name__ + str(self)

    def contains(self, x: Real) -> bool:
        leftIn = self.beg is None or x > self.beg or (x >= self.beg and self.begClosed)
        rightIn = self.end is None or x < self.end or (x <= self.end and self.endClosed)
        return leftIn and rightIn

    def isEmpty(self) -> bool:
        return self.beg is not None and self.end is not None and (
            self.beg > self.end or (self.beg >= self.end and not (self.begClosed and self.endClosed)))

    def equals(self, other: Interval) -> bool:
        return (self.beg == other.beg and self.begClosed is other.begClosed
            and self.end == other.end and self.endClosed is other.endClosed)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Interval):
            return self.equals(other)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash((self.beg, self.end, self.begClosed, self.endClosed))

    def intersect(self, other: Interval) -> Interval:
        beg: Optional[Real]
        begClosed: bool
        if self.beg is None:
            if other.beg is None:
                beg, begClosed = None, self.begClosed and other.begClosed
            else:
                beg, begClosed = other.beg, other.begClosed
        elif other.beg is None or other.beg < self.beg:
            beg, begClosed = self.beg, self.begClosed
        elif self.beg < other.beg:
            beg, begClosed = other.beg, other.begClosed
        else:  # self.beg == other.beg
            beg, begClosed = self.beg, self.begClosed and other.begClosed

        end: Optional[Real]
        endClosed: bool
        if self.end is None:
            if other.end is None:
                end, endClosed = None, self.endClosed and other.endClosed
            else:
                end, endClosed = other.end, other.endClosed
        elif other.end is None or self.end < other.end:
            end, endClosed = self.end, self.endClosed
        elif other.end < self.end:
            end, endClosed = other.end, other.endClosed
        else:  # self.end == other.end
            end, endClosed = self.end, self.endClosed and other.endClosed

        return Interval(beg, end, begClosed, endClosed)

    def __and__(self, other: Interval) -> Interval:
        return self.intersect(other)

    def containsSet(self, other: Interval) -> bool:
        return self.intersect(other).equals(other)

    def isDisjoint(self, other: Interval) -> bool:
        return self.intersect(other).isEmpty()
