import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from ...model.enum.status import Status
from ...repositories.transaction_repository import (
    fetch_transactions,
    remove_transaction,
)
from ...services.transaction_service import (
    CategoryNotFoundError,
    InvalidPaidDateError,
    TransactionNotFoundError,
    modify_transaction,
)
from ..dependencies import APP_ONLY, APP_OR_BOT, MONTH_PATTERN, get_conn
from ..schemas import TransactionOut, TransactionUpdateIn

router = APIRouter()


@router.get(
    "/transactions", response_model=list[TransactionOut], dependencies=[APP_OR_BOT]
)
def get_transactions(
    month: str | None = Query(None, pattern=MONTH_PATTERN),
    status: Status | None = None,
    source_ref: str | None = None,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    transactions = fetch_transactions(
        conn, month=month, status=status, source_ref=source_ref
    )
    return [TransactionOut.from_model(t) for t in transactions]


@router.patch(
    "/transactions/{transaction_id}",
    response_model=TransactionOut,
    dependencies=[APP_OR_BOT],
)
def patch_transaction(
    transaction_id: int,
    body: TransactionUpdateIn,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        transaction = modify_transaction(conn, transaction_id, body.to_model())
    except TransactionNotFoundError:
        raise HTTPException(status_code=404, detail="Transaction not found") from None
    except CategoryNotFoundError:
        raise HTTPException(status_code=422, detail="Category not found") from None
    except InvalidPaidDateError:
        raise HTTPException(
            status_code=400, detail="paid_date must not be before occurred_date"
        ) from None
    return TransactionOut.from_model(transaction)


@router.delete(
    "/transactions/{transaction_id}", status_code=204, dependencies=[APP_ONLY]
)
def delete_transaction(
    transaction_id: int,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    if not remove_transaction(conn, transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")
