from dataclasses import dataclass


@dataclass(frozen=True)
class Setting:
    id: int
    monthly_budget: int
    gmail_label: str
