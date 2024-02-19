#!/usr/bin/env python3

import sys  # noqa
import unittest
from code2dtree.expr import Var, BinExpr
from code2dtree.interval import Interval
from code2dtree.linExpr import parseLinCmpExpr, LinCmpExpr
from code2dtree.linExpr import addConstrToDict, ConstrDict, LinConstrTreeExplorer, IneqMode
from code2dtree.linExpr import displayConstraints  # noqa
from code2dtree.linProg import LinProg, DEFAULT_BOUND, LpStatus


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
        addConstrToDict(x - y >= 2, True, constraints, IneqMode.exact)
        addConstrToDict(x - y <= 2, True, constraints, IneqMode.exact)
        addConstrToDict(y - x <= -1, True, constraints, IneqMode.exact)
        self.assertEqual(len(constraints), 1)
        ((coeffs, interval),) = list(constraints.items())
        self.assertEqual({k for k, v in coeffs}, {'x', 'y'})
        self.assertEqual({v for k, v in coeffs}, {-1, 1})
        self.assertIn(interval, (Interval.fromStr('[2,2]'), Interval.fromStr('[-2,-2]')))

    def testEmpty(self) -> None:
        constraints: ConstrDict = {}
        x = Var.get('x')
        addConstrToDict(x >= x, True, constraints, IneqMode.exact)
        addConstrToDict(True, True, constraints, IneqMode.exact)
        self.assertEqual(constraints, {})

    def testModes(self) -> None:
        constraints: ConstrDict = {}
        x, y = Var.get('x'), Var.get('y')

        addConstrToDict(x > 2, True, constraints, IneqMode.lenient)
        addConstrToDict(x < 2, True, constraints, IneqMode.lenient)
        (interval,) = list(constraints.values())
        self.assertEqual(interval, Interval.fromStr('[2,2]'))

        constraints.clear()
        addConstrToDict(y >= 2, True, constraints, IneqMode.strict)
        addConstrToDict(y < 3, True, constraints, IneqMode.strict)
        (interval,) = list(constraints.values())
        self.assertEqual(interval, Interval.fromStr('(2,3)'))


class ConstrDecideTest(unittest.TestCase):
    def test1(self) -> None:
        x, y = Var.get('x'), Var.get('y')
        te = LinConstrTreeExplorer([x > 0])
        self.assertEqual(te.decideIf(x <= 2)[1], True)
        self.assertEqual(te.decideIf(x + y <= 2)[1], True)

    def test2(self) -> None:
        x = Var.get('x')
        te = LinConstrTreeExplorer([x > 0])
        decision, checkOther, sexpr = te.decideIf(x <= -2)
        self.assertEqual((decision, checkOther), (False, False))
        decision, checkOther, sexpr = te.decideIf(x > x)
        self.assertEqual((decision, checkOther), (False, False))


class LinCmpExprTest(unittest.TestCase):
    def testStr(self) -> None:
        x, y = Var.get('x'), Var.get('y')
        expr1 = parseLinCmpExpr(x - 2 * y >= 3, IneqMode.exact)
        expr2 = LinCmpExpr({'x': 1, 'y': -2, 'z': 0}, '≥', 3)
        s = '(x - 2 * y ≥ 3)'
        self.assertEqual(str(expr1), s)
        self.assertEqual(str(expr2), s)


class LinProgTest(unittest.TestCase):
    def testFlatten(self) -> None:
        x, y = Var.get('x'), Var.get('y')
        int23 = Interval(2, 3, True, True)
        lp = LinProg('min', [x, [x, y], {'z': int23}], 2 - 3 * x)
        self.assertEqual(lp.varNames, ['x', 'y', 'z'])
        self.assertEqual(lp.varNameToIndex, {'x': 0, 'y': 1, 'z': 2})
        self.assertEqual(lp.varBounds, [DEFAULT_BOUND, DEFAULT_BOUND, int23])
        self.assertEqual(lp.objConst, 2)
        self.assertEqual(lp.objVec, [-3, 0, 0])

    def getLp(self) -> LinProg:
        x, y = Var.get('x'), Var.get('y')
        lp = LinProg('max', ['x', y], x + y + 1)
        lp.addConstraintExpr(2*x + 3*y <= 13)
        lp.addConstraintExpr(2*x + y < 7.1)
        lp.addConstraintExpr(x + y >= 3)
        lp.addConstraintExpr(x - x >= 0)
        return lp

    def testScipyInput(self) -> None:
        import numpy as np
        lp = self.getLp()
        # print(lp)
        scipyInput = lp.copy().getScipyInput(0.1)
        self.assertIsNotNone(scipyInput)
        assert scipyInput is not None  # for type checking
        self.assertTrue(np.array_equal(scipyInput.c, [-1, -1]))
        self.assertTrue(np.array_equal(scipyInput.A_eq, np.zeros((0, 2))))
        self.assertTrue(np.array_equal(scipyInput.b_eq, np.zeros((0,))))
        self.assertTrue(np.array_equal(scipyInput.A_ub, [[2, 3], [2, 1], [-1, -1]]))
        self.assertTrue(np.array_equal(scipyInput.b_ub, [13, 7, -3]))
        defaultBound = (0, None)
        self.assertTrue(scipyInput.bounds, [defaultBound] * 2)

    def testSolve(self) -> None:
        import numpy as np
        lp = self.getLp()
        # print(lp)
        res = lp.solve(tol=0.1)
        # print(res)
        self.assertEqual(res.status, LpStatus.success)
        self.assertTrue(np.array_equal(res.optSol, [2, 3]))
        self.assertEqual(res.optVal, 6)


if __name__ == '__main__':
    unittest.main()
