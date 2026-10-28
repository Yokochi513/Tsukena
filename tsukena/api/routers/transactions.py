import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from ...model.enum.status import Status
from ...repositories.transaction_repository import fetch_transactions
from ...services.payment_plan_service import PlanNotAvailableError
from ...services.transaction_service import (
    CategoryNotFoundError,
    InvalidPaidDateError,
    TransactionNotFoundError,
    delete_transaction,
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
    q: str | None = None,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    transactions = fetch_transactions(
        conn, month=month, status=status, source_ref=source_ref, q=q
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
    except PlanNotAvailableError:
        # 支払い方法を変えたあとで、設定から手数料率などを消した
        raise HTTPException(
            status_code=409,
            detail="Payment plan is not available for this payment method",
        ) from None
    return TransactionOut.from_model(transaction)


@router.delete(
    "/transactions/{transaction_id}", status_code=204, dependencies=[APP_ONLY]
)
def delete_transaction_endpoint(
    transaction_id: int,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    if not delete_transaction(conn, transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")
