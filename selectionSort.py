#!/usr/bin/env python3

import sys
from code2dtree import Var, RepeatedRunDTreeGen


def selectionSorted(a):
    a = a.copy()
    n = len(a)
    for i in range(n):
        for j in range(i+1, n):
            if a[i] > a[j]:
                a[j], a[i] = a[i], a[j]
    return a


def main():
    n = int(input('Enter number of elements in list to sort: '))
    a = [Var('x'+str(i)) for i in range(n)]
    print('input:', a)
    gen = RepeatedRunDTreeGen()
    gen.run(selectionSorted, a)
    gen.root.print(sys.stdout)


if __name__ == '__main__':
    main()
