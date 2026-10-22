from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    emoji: str
    sort_order: int


@dataclass(frozen=True)
class CategoryInput:
    name: str
    emoji: str
    # 追加では省略すると末尾、変更では省略すると今の表示順のまま
    sort_order: int | None = None
