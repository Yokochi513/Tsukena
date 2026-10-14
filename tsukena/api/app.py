import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ..repositories.database import connect
from ..repositories.expense_repository import list_expenses
from .schemas import ExpenseOut


def create_app(db_path: Path) -> FastAPI:
    app = FastAPI(title="Tsukena API")
    app.state.db_path = db_path  # ① 設定を app に持たせる
    # Flutter Web の開発サーバーはポートが毎回変わるため、ローカルのオリジンをポート問わず許可する
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET"],
    )

    @app.get("/expenses", response_model=list[ExpenseOut])
    def get_expenses(conn: sqlite3.Connection = Depends(get_conn)):  # ③
        return [ExpenseOut.from_model(e) for e in list_expenses(conn)]  # ④

    return app


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
