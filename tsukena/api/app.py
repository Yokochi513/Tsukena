import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from ..model.enum.status import Status
from ..repositories.category_repository import (
    fetch_categories,
    insert_category,
    update_category,
)
from ..repositories.database import connect
from ..repositories.expense_repository import list_expenses
from ..repositories.income_repository import (
    fetch_incomes,
    insert_income,
    remove_income,
    update_income,
)
from ..repositories.transaction_repository import fetch_transactions
from ..services.transaction_service import (
    CategoryNotFoundError,
    InvalidPaidDateError,
    TransactionNotFoundError,
    modify_transaction,
)
from .schemas import (
    CategoryIn,
    CategoryOut,
    ExpenseOut,
    IncomeIn,
    IncomeOut,
    TransactionOut,
    TransactionUpdateIn,
)

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def create_app(db_path: Path) -> FastAPI:
    app = FastAPI(title="Tsukena API")
    app.state.db_path = db_path  # ① 設定を app に持たせる
    # Flutter Web の開発サーバーはポートが毎回変わるため、ローカルのオリジンをポート問わず許可する
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
    )

    @app.get("/expenses", response_model=list[ExpenseOut])
    def get_expenses(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [ExpenseOut.from_model(e) for e in list_expenses(conn)]

    @app.get("/transactions", response_model=list[TransactionOut])
    def get_transactions(
        month: str | None = Query(None, pattern=MONTH_PATTERN),
        status: Status | None = None,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        return [
            TransactionOut.from_model(t)
            for t in fetch_transactions(conn, month=month, status=status)
        ]

    @app.patch("/transactions/{transaction_id}", response_model=TransactionOut)
    def patch_transaction(
        transaction_id: int,
        body: TransactionUpdateIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        try:
            transaction = modify_transaction(conn, transaction_id, body.to_model())
        except TransactionNotFoundError:
            raise HTTPException(
                status_code=404, detail="Transaction not found"
            ) from None
        except CategoryNotFoundError:
            raise HTTPException(status_code=422, detail="Category not found") from None
        except InvalidPaidDateError:
            raise HTTPException(
                status_code=400, detail="paid_date must not be before occurred_date"
            ) from None
        return TransactionOut.from_model(transaction)

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

    @app.delete("/incomes/{income_id}", status_code=204)
    def delete_income(income_id: int, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        if not remove_income(conn, income_id):
            raise HTTPException(status_code=404, detail="Income not found")

    @app.get("/categories", response_model=list[CategoryOut])
    def get_categories(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [CategoryOut.from_model(category) for category in fetch_categories(conn)]

    @app.post("/categories", response_model=CategoryOut, status_code=201)
    def post_category(body: CategoryIn, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return CategoryOut.from_model(insert_category(conn, body.to_model()))

    @app.patch("/categories/{category_id}", response_model=CategoryOut)
    def patch_category(
        category_id: int,
        body: CategoryIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        category = update_category(conn, category_id, body.to_model())

        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return CategoryOut.from_model(category)

    return app


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
