#!/usr/bin/env python3

"""Longest Processing Time (LPT) algorithm for makespan minimization."""

import argparse
from collections.abc import Generator, Iterable, Sequence
import os.path
import subprocess
import json
from typing import NamedTuple

from code2dtree import Expr, genFunc2dtree, getVarList
from code2dtree.node import dtreeToFlatJson, printGraphViz, PrintOptions, PrintStatus
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


def greedy(x: Iterable[Real | Expr], m: int) -> Generator[AssnEvent, None, Sequence[int]]:
    """Jobs have sizes x. There are m machines."""
    assn = []
    jobGen = iter(x)
    loads = []
    for j, xj in zip(range(m), jobGen):
        yield AssnEvent(job=j, machine=j)
        assn.append(j)
        loads.append(xj)
    for j, xj in enumerate(jobGen, m):
        i = argmin(loads)
        yield AssnEvent(job=j, machine=i)
        assn.append(i)
        loads[i] += xj
    return assn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('n', type=int, help='number of jobs')
    parser.add_argument('m', type=int, help='number of machines')
    parser.add_argument('-o', '--output', help='path to output (dot, svg)')
    parser.add_argument('--lineNo', action='store_true', default=False,
        help='display line numbers')
    args = parser.parse_args()

    print('n={n} jobs, m={m} machines'.format(n=args.n, m=args.m))
    x = getVarList('x', args.n, style='simple')
    te = LinConstrTreeExplorer([x[i-1] >= x[i] for i in range(1, args.n)])
    dtree = genFunc2dtree(greedy, (x, args.m), te)
    if args.output is not None:
        baseName, ext = os.path.splitext(args.output)
        if ext == '.dot':
            with open(args.output, 'w') as fp:
                printGraphViz(dtree, fp)
        elif ext == '.svg':
            dotName = args.output + '.dot'
            with open(dotName, 'w') as fp:
                printGraphViz(dtree, fp)
            subprocess.run(['dot', '-T', 'svg', dotName, '-o', args.output], check=True)
        elif ext == '.json':
            jsonObj = dtreeToFlatJson(dtree)
            with open(args.output, 'w') as fp:
                json.dump(jsonObj, fp, indent=4)
        else:
            raise ValueError('unsupported output extension ' + ext)
    else:
        lineNoCols = 4 if args.lineNo else 0
        options = PrintOptions(lineNoCols=lineNoCols)
        status = PrintStatus()
        dtree.print(options, status)
        print(f'\nnodes: {status.nodes}, leaves: {status.leaves}, lines={status.lines}')


if __name__ == '__main__':
    main()
