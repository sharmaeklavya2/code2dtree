from __future__ import annotations
from abc import abstractmethod
from typing import TypeVar
from typing_extensions import Protocol
from fractions import Fraction


CompT = TypeVar('CompT', bound='Comparable')
Real = int | float | Fraction


def validateRealness(x: object) -> Real:
    assert isinstance(x, int) or isinstance(x, float) or isinstance(x, Fraction)
    return x


def strToIntOrFloat(s: str) -> int | float:
    try:
        return int(s)
    except ValueError:
        s = s.replace('∞', 'inf')
        return float(s)


def strToReal(s: str) -> Real:
    parts = s.split('/')
    if len(parts) == 2:
        return Fraction(int(parts[0]), int(parts[1]))
    elif len(parts) == 1:
        return strToIntOrFloat(parts[0])
    else:
        raise ValueError('too many slashes')


class Comparable(Protocol):
    # from https://github.com/python/typing/issues/59#issuecomment-353878355
    @abstractmethod
    def __eq__(self, other: object) -> bool:
        pass

    @abstractmethod
    def __lt__(self: CompT, other: CompT) -> bool:
        pass

    def __gt__(self: CompT, other: CompT) -> bool:
        return (not self < other) and self != other

    def __le__(self: CompT, other: CompT) -> bool:
        return self < other or self == other

    def __ge__(self: CompT, other: CompT) -> bool:
        return (not self < other)
