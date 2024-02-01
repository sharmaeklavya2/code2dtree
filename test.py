#!/usr/bin/env python3

import sys  # noqa
import unittest
from code2dtree import Var, BinExpr
from code2dtree.interval import Interval
from code2dtree.linExpr import addConstrToDict, ConstrDict, LinConstrTreeExplorer
from code2dtree.linExpr import displayConstraints  # noqa


class ExprTest(unittest.TestCase):
    def testOpOverload1(self) -> None:
        x, y = Var.get('x'), Var.get('y')
        automatic = (x + y) * (x - y)
        manual = BinExpr('*', BinExpr('+', x, y), BinExpr('-', x, y))
        self.assertEqual(automatic.key(), manual.key())

    def testOpOverload2(self) -> None:
        x = Var.get('x')
        automatic = 1 - x * 2
        manual = BinExpr('-', 1, BinExpr('*', x, 2))
        self.assertEqual(automatic.key(), manual.key())


class IntervalTest(unittest.TestCase):
    def testContains1(self) -> None:
        interval = Interval.fromStr('[2, 3)')
        self.assertFalse(interval.contains(1))
        self.assertTrue(interval.contains(2))
        self.assertTrue(interval.contains(2.5))
        self.assertFalse(interval.contains(3))
        self.assertFalse(interval.contains(3.5))

    def testContains2(self) -> None:
        interval = Interval.fromStr('(2, 3]')
        self.assertFalse(interval.contains(1))
        self.assertFalse(interval.contains(2))
        self.assertTrue(interval.contains(2.5))
        self.assertTrue(interval.contains(3))
        self.assertFalse(interval.contains(3.5))

    def testIsEmpty(self) -> None:
        self.assertTrue(Interval.fromStr('[3, 2]').isEmpty())
        self.assertFalse(Interval.fromStr('[2, 2]').isEmpty())
        self.assertTrue(Interval.fromStr('(2, 2]').isEmpty())
        self.assertTrue(Interval.fromStr('[2, 2)').isEmpty())
        self.assertTrue(Interval.fromStr('(2, 2)').isEmpty())
        self.assertFalse(Interval.fromStr('(2, 3)').isEmpty())

    def testIntersect(self) -> None:
        self.assertEqual(Interval.fromStr('[2, 4)') & Interval.fromStr('(3, 5]'),
            Interval.fromStr('(3, 4)'))
        self.assertTrue(Interval.fromStr('[2, 4)').isDisjoint(Interval.fromStr('[4, 5]')))


class ConstrAddTest(unittest.TestCase):
    def testOpposite(self) -> None:
        constraints: ConstrDict = {}
        x, y = Var.get('x'), Var.get('y')
        addConstrToDict(x - y >= 2, True, constraints)
        addConstrToDict(x - y <= 2, True, constraints)
        addConstrToDict(y - x <= -1, True, constraints)
        self.assertEqual(len(constraints), 1)
        ((coeffs, interval),) = list(constraints.items())
        self.assertEqual({k for k, v in coeffs}, {'x', 'y'})
        self.assertEqual({v for k, v in coeffs}, {-1, 1})
        self.assertIn(interval, (Interval.fromStr('[2,2]'), Interval.fromStr('[-2,-2]')))

    def testEmpty(self) -> None:
        constraints: ConstrDict = {}
        x = Var.get('x')
        addConstrToDict(x >= x, True, constraints)
        addConstrToDict(True, True, constraints)
        self.assertEqual(constraints, {})


class ConstrDecideTest(unittest.TestCase):
    def test1(self) -> None:
        x, y = Var.get('x'), Var.get('y')
        te = LinConstrTreeExplorer([x > 0])
        self.assertEqual(te.decideIf(x <= 2)[1], True)
        self.assertEqual(te.decideIf(x + y <= 2)[1], True)

    def test2(self) -> None:
        x = Var.get('x')
        te = LinConstrTreeExplorer([x > 0])
        self.assertEqual(te.decideIf(x <= -2), (False, False))
        self.assertEqual(te.decideIf(x > x), (False, False))


if __name__ == '__main__':
    unittest.main()
