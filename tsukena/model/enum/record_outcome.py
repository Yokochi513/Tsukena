from enum import StrEnum


class RecordOutcome(StrEnum):
    RECORDED = "recorded"
    DUPLICATE = "duplicate"  # 同じ重複排除キーの記録が既にある
    DELETED = "deleted"  # 同じ重複排除キーの記録が過去に削除されている
