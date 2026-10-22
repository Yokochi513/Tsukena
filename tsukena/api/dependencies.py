import sqlite3
from collections.abc import Iterator

from fastapi import Depends, Request

from ..repositories.database import connect
from .auth import Caller, allow

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
APP_ONLY = Depends(allow(Caller.APP))
APP_OR_BOT = Depends(allow(Caller.APP, Caller.BOT))
BOT_ONLY = Depends(allow(Caller.BOT))


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
