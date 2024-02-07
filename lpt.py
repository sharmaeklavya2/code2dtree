#!/usr/bin/env python3

"""Longest Processing Time (LPT) algorithm for makespan minimization."""

import sys
import argparse
from collections.abc import Generator, Sequence
from typing import NamedTuple
from code2dtree import Expr, genFunc2dtree, getVarList, printGraphViz
from code2dtree.linExpr import LinConstrTreeExplorer
from code2dtree.types import Real


def argmin(x: Sequence[Real | Expr]) -> int:
    """Largest index of minimum value in non-empty list."""
    n = len(x)
    minIndex, minValue = 0, x[0]
    for i in range(1, n):
        if x[i] <= minValue:
            minIndex, minValue = i, x[i]
    return minIndex


class AssnEvent(NamedTuple):
    job: int
    machine: int


def greedy(x: Sequence[Real | Expr], m: int) -> Generator[AssnEvent, None, Sequence[int]]:
    """Jobs have sizes x. There are m machines."""
    n = len(x)
    minMN = min(m, n)
    assn = list(range(minMN))
    for j in range(minMN):
        yield AssnEvent(job=j, machine=j)
    if n <= m:
        return assn
    loads = list(x[:m])
    for j in range(m, n):
        i = argmin(loads)
        assn.append(i)
        loads[i] += x[j]
        yield AssnEvent(job=j, machine=i)
    return assn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, help='number of jobs')
    parser.add_argument('m', type=int, help='number of machines')
    parser.add_argument('-o', '--output', help='path to dot output file')
    args = parser.parse_args()

    print('n={n} jobs, m={m} machines'.format(n=args.n, m=args.m))
    x = getVarList('x', args.n, False)
    te = LinConstrTreeExplorer([x[i-1] >= x[i] for i in range(1, args.n)])
    dtree = genFunc2dtree(greedy, (x, args.m), te)
    if args.output is not None:
        with open(args.output, 'w') as fp:
            printGraphViz(dtree, fp)
    else:
        dtree.print(sys.stdout)


if __name__ == '__main__':
    main()
