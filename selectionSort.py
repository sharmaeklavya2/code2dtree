#!/usr/bin/env python3

import argparse
from code2dtree import func2dtree, getVarList
from code2dtree.nodeIO import printTree, printGraphViz
from code2dtree.types import CompT


def selectionSorted(a: list[CompT]) -> list[CompT]:
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

    a = getVarList('a', args.n)
    print('input:', a)
    dtree = func2dtree(selectionSorted, (a,))
    if args.output is not None:
        with open(args.output, 'w') as fp:
            printGraphViz(dtree, fp)
    else:
        printTree(dtree)


if __name__ == '__main__':
    main()
