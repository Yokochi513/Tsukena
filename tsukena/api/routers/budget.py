import sqlite3

from fastapi import APIRouter, Depends

from ...repositories.setting_repository import fetch_setting, update_monthly_budget
from ..dependencies import APP_ONLY, get_conn
from ..schemas import BudgetIn, BudgetOut

router = APIRouter()


@router.get("/budget", response_model=BudgetOut, dependencies=[APP_ONLY])
def get_budget(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
    return BudgetOut(monthly_budget=fetch_setting(conn).monthly_budget)


# 予算は全体で1つだけ持つ。変えると過去の月の集計もこの値で計算される（→ docs/api_list.md 2.5）
@router.put("/budget", response_model=BudgetOut, dependencies=[APP_ONLY])
def put_budget(body: BudgetIn, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
    update_monthly_budget(conn, body.monthly_budget)
    return BudgetOut(monthly_budget=fetch_setting(conn).monthly_budget)
