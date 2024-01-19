# Code to Decision Tree

Convert a python function to a decision tree.

Run `python selectionSort.py 3` to get a decision tree for
the [selection sort](https://en.wikipedia.org/wiki/Selection_sort) algorithm
when the input is a list of length 3.
Read `selectionSort.py` and `lpt.py` to see how to use `code2dtree`.

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
