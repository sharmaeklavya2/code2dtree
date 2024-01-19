from .expr import Expr


class TreeExplorer:
    def decideIf(self, expr: Expr) -> tuple[bool, bool]:
        # return pair (b1, b2), where b1 = bool(expr) and b2 decides whether
        # not(expr) should be explored in the future.
        return (False, True)

    def noteIf(self, expr: Expr, b: bool) -> None:
        pass

    def noteReturn(self, expr: object) -> None:
        pass


class CachedTreeExplorer(TreeExplorer):
    def __init__(self) -> None:
        super().__init__()
        self.cache: dict[object, bool] = {}

    def noteIf(self, expr: Expr, b: bool) -> None:
        key = expr.key()
        self.cache[key] = b

    def decideIf(self, expr: Expr) -> tuple[bool, bool]:
        key = expr.key()
        try:
            b = self.cache[key]
            return (b, False)
        except KeyError:
            self.cache[key] = False
            return (False, True)

    def noteReturn(self, expr: object) -> None:
        self.cache.clear()
