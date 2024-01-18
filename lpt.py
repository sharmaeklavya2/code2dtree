#!/usr/bin/env python3

"""Longest Processing Time (LPT) algorithm for makespan minimization."""

import sys
import argparse
from code2dtree import Var, func2dtree, printGraphViz, FuncArgs
from code2dtree.linExpr import LinConstrTreeExplorer
from collections.abc import Sequence
from typing import Any


CompT = Any


def argmin(x: Sequence[CompT]) -> CompT:
    """Smallest index of minimum value in non-empty list."""
    n = len(x)
    minIndex, minValue = 0, x[0]
    for i in range(1, n):
        if x[i] < minValue:
            minIndex, minValue = i, x[i]
    return minIndex


def lpt(x: Sequence[CompT], m: int) -> Sequence[int]:
    """Jobs have sizes x. There are m machines."""
    n = len(x)
    if n <= m:
        return list(range(n))

    assn = list(range(m))
    assn.append(m-1)
    loads = list(x[:m])
    loads[m-1] += x[m]
    for j in range(m+1, n):
        i = argmin(loads)
        assn.append(i)
        loads[i] += x[j]
    return assn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, help='number of jobs')
    parser.add_argument('m', type=int, help='number of machines')
    parser.add_argument('-o', '--output', help='path to dot output file')
    args = parser.parse_args()

    varNames = ['x'+str(i) for i in range(args.n)]
    x = [Var(varName) for varName in varNames]
    print('n={n} jobs, m={m} machines'.format(n=args.n, m=args.m))
    dtree = func2dtree(lpt, FuncArgs(x, args.m), LinConstrTreeExplorer(orderings=(varNames,)))
    if args.output is not None:
        with open(args.output, 'w') as fp:
            printGraphViz(dtree, fp)
    else:
        dtree.print(sys.stdout)


if __name__ == '__main__':
    main()
