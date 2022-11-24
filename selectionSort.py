#!/usr/bin/env python3

import sys
import argparse
from code2dtree import Var, RepeatedRunDTreeGen, toVE, printGraphViz


def selectionSorted(a):
    a = a.copy()
    n = len(a)
    for i in range(n):
        for j in range(i+1, n):
            if a[i] > a[j]:
                a[j], a[i] = a[i], a[j]
    return a


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, help='number of elements in list to sort')
    parser.add_argument('-o', '--output', help='path to dot output file')
    args = parser.parse_args()

    a = [Var('x'+str(i)) for i in range(args.n)]
    print('input:', a)
    gen = RepeatedRunDTreeGen()
    gen.run(selectionSorted, a)
    if args.output is not None:
        V, E = toVE(gen.root)
        with open(args.output, 'w') as fp:
            printGraphViz(V, E, fp)
    else:
        gen.root.print(sys.stdout)


if __name__ == '__main__':
    main()
