"""Module summary line.

More detail.
"""


def documented(a: int, b: str = "x") -> bool:
    """Do a thing.

    Args:
        a: the first number.
        b (str): a label.

    Returns:
        True when it worked.

    Raises:
        ValueError: when a is negative.
    """
    return True


def undocumented(x):
    return x


def _private():
    """Hidden."""


class Widget:
    """A widget.

    :param size: the size.
    :returns: nothing
    """

    def render(self):
        """Render it."""

    def _internal(self):
        pass
