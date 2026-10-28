import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Charge:
    """支出の1回分の引き落とし。1回払いなら、支払日に金額の全部を1回で引き落とす"""

    seq: int  # 何回目か（1 から）
    paid_date: datetime.date
    principal: int  # 元金
    fee: int  # 手数料
    fee_edited: bool = False  # 手数料をアプリで直したか

    @property
    def amount(self) -> int:
        return self.principal + self.fee


@dataclass(frozen=True)
class RevolvingMonth:
    """リボ払いの、ある支払い手段のひと月分の引き落とし（リボにした支出の全部を合わせた額）"""

    month: str  # YYYY-MM
    paid_date: datetime.date
    principal: int
    fee: int
    fee_edited: bool  # その月の手数料をアプリで直したか
    balance: int  # 引き落としのあとに残る元金
