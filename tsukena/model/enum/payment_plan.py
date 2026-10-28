from enum import StrEnum


class PaymentPlan(StrEnum):
    """支払い方法（→ docs/adr/0011）"""

    LUMP = "lump"  # 1回払い
    SKIP = "skip"  # スキップ払い。支払い月を先に送り、1回で払う
    INSTALLMENT = "installment"  # 分割払い
    REVOLVING = "revolving"  # リボ払い
