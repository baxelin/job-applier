from collections import Counter
from collections.abc import Iterable


class UniquenessChecker:
    """Garante que uma coleção de valores não tem repetições."""

    @staticmethod
    def ensure_unique(values: Iterable[str], description: str) -> None:
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            raise ValueError(f"{description} repetidos: {', '.join(duplicates)}")
