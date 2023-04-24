# Code to Decision Tree

`code2dtree` converts a python function to a decision tree.

For example, for this sorting algorithm

```python
def selectionSorted(a):
    a = a.copy()
    n = len(a)
    for i in range(n):
        for j in range(i+1, n):
            if a[i] > a[j]:
                a[j], a[i] = a[i], a[j]
    return a
```

the decision tree is

<img src="https://github.com/sharmaeklavya2/code2dtree/blob/with-examples/examples/ss3.svg?raw=true" />

Read `selectionSort.py` to see how to generate this decision tree using `code2dtree`.
Running `python selectionSort.py 3` will print a text version of the above decision tree.

`code2dtree` contains type annotations. It passes the `mypy --strict` check.

## How it works

Currently, `code2dtree` works by running the function multiple times
with dummy input to probe all parts of it.

I'll take comparison sorting algorithms as an example.
Whenever a comparison happens, instead of actually performing the comparison
(which isn't possible, since the dummy input isn't actually numbers),
we carefully decide whether to return `True` or `False` in order
to systematically explore the function.
To do this, we create a custom class, called `Var` (variable),
and overload its comparison operator. The dummy input is a list of `Var` objects.

To handle algorithms other than comparison sorting, e.g., algorithms involving arithmetic,
we overload arithmetic and relational operators to return `Expr` (expression) objects,
and we overload the conversion-to-boolean operator
([`__bool__`](https://docs.python.org/3/reference/datamodel.html#object.__bool__))
for systematic exploration of the function.

This approach can be inefficient. If the decision tree is very unbalanced,
then the worst-case time to construct a decision tree having `n` leaves is `Θ(n²)`.
A few other approaches are mentioned here, but they seem a lot harder to implement:
<https://stackoverflow.com/q/74541481>.
