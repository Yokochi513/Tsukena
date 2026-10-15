import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from ..repositories.database import connect
from ..repositories.expense_repository import list_expenses
from ..repositories.income_repository import fetch_incomes, insert_income, update_income
from .schemas import ExpenseOut, IncomeIn, IncomeOut


def create_app(db_path: Path) -> FastAPI:
    app = FastAPI(title="Tsukena API")
    app.state.db_path = db_path  # ① 設定を app に持たせる
    # Flutter Web の開発サーバーはポートが毎回変わるため、ローカルのオリジンをポート問わず許可する
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST"],
    )

    @app.get("/expenses", response_model=list[ExpenseOut])
    def get_expenses(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [ExpenseOut.from_model(e) for e in list_expenses(conn)]

    @app.get("/incomes", response_model=list[IncomeOut])
    def get_incomes(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [IncomeOut.from_model(income) for income in fetch_incomes(conn)]

    @app.post("/incomes", response_model=IncomeOut, status_code=201)
    def post_income(
        body: IncomeIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        return IncomeOut.from_model(insert_income(conn, body.to_model()))

    @app.patch("/incomes/{income_id}", response_model=IncomeOut)
    def patch_income(
        income_id: int,
        body: IncomeIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        income = update_income(conn, income_id, body.to_model())

        if income is None:
            raise HTTPException(status_code=404, detail="Income not found")
        return IncomeOut.from_model(income)

    return app


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
