import sqlite3

from fastapi import APIRouter, Depends, Path

from ...repositories.summary_repository import fetch_monthly_summary
from ..dependencies import APP_ONLY, MONTH_PATTERN, get_conn
from ..schemas import MonthlySummaryOut

router = APIRouter()


# 記録も収入も無い月や来月以降の月でも 404 にせず、合計を0で返す（→ docs/api_list.md 2.1）
@router.get(
    "/months/{month}/summary",
    response_model=MonthlySummaryOut,
    dependencies=[APP_ONLY],
)
def get_monthly_summary(
    month: str = Path(pattern=MONTH_PATTERN),
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    return MonthlySummaryOut.from_model(fetch_monthly_summary(conn, month))
