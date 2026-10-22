import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from ...repositories.income_repository import (
    fetch_incomes,
    insert_income,
    remove_income,
    update_income,
)
from ..dependencies import APP_ONLY, MONTH_PATTERN, get_conn
from ..schemas import IncomeIn, IncomeOut

router = APIRouter()


# 収入の一覧は常に月を指定して開くため、month は省略できない（→ docs/api_list.md 2.3）
@router.get("/incomes", response_model=list[IncomeOut], dependencies=[APP_ONLY])
def get_incomes(
    month: str = Query(pattern=MONTH_PATTERN),
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    return [IncomeOut.from_model(income) for income in fetch_incomes(conn, month)]


@router.post(
    "/incomes", response_model=IncomeOut, status_code=201, dependencies=[APP_ONLY]
)
def post_income(
    body: IncomeIn,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    return IncomeOut.from_model(insert_income(conn, body.to_model()))


@router.patch("/incomes/{income_id}", response_model=IncomeOut, dependencies=[APP_ONLY])
def patch_income(
    income_id: int,
    body: IncomeIn,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    income = update_income(conn, income_id, body.to_model())

    if income is None:
        raise HTTPException(status_code=404, detail="Income not found")
    return IncomeOut.from_model(income)


@router.delete("/incomes/{income_id}", status_code=204, dependencies=[APP_ONLY])
def delete_income(income_id: int, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
    if not remove_income(conn, income_id):
        raise HTTPException(status_code=404, detail="Income not found")
