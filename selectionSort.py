#!/usr/bin/env python3

import sys
import argparse
from code2dtree import Var, func2dtree, printGraphViz
from typing import Any


def selectionSorted(a: list[Any]) -> list[Any]:
    a = a.copy()
    n = len(a)
    for i in range(n):
        for j in range(i+1, n):
            if a[i] > a[j]:
                a[j], a[i] = a[i], a[j]
    return a


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, help='number of elements in list to sort')
    parser.add_argument('-o', '--output', help='path to dot output file')
    args = parser.parse_args()

    a = [Var('x'+str(i)) for i in range(args.n)]
    print('input:', a)
    dtree = func2dtree(selectionSorted, a)
    if args.output is not None:
        with open(args.output, 'w') as fp:
            printGraphViz(dtree, fp)
    else:
        dtree.print(sys.stdout)


if __name__ == '__main__':
    main()
