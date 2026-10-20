from dataclasses import dataclass


@dataclass(frozen=True)
class Setting:
    id: int
    monthly_budget: int
    gmail_label: str
    full_import_done: bool  # 全期間の取り込みを済ませたか（→ docs/design.md 4.1）
