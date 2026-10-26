def typed(a: int, b: str = '') -> bool:
    return True


def untyped(a, b):
    return a


class C:
    def __init__(self, x: int):
        self.x = x

    def m(self, y) -> None:
        pass
