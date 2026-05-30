from dataclasses import dataclass


@dataclass
class PeriodCreateResult:
    """Результат создания периода. already_exists — период уже был (переключились)."""

    already_exists: bool
    copied_count: int
