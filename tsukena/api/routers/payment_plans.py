import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Path

from ...services.payment_plan_service import (
    ChargeNotFoundError,
    FeeNotEditableError,
    InvalidPlanCountError,
    PlanNotAvailableError,
    TransactionNotFoundError,
    change_payment_plan,
    fetch_revolving,
    set_charge_fee,
    set_revolving_fee,
)
from ..dependencies import APP_ONLY, MONTH_PATTERN, get_conn
from ..schemas import FeeIn, PaymentPlanIn, RevolvingMonthOut, TransactionOut

# 支払い方法の変更と、引き落とし額の手直し（→ docs/adr/0011）
router = APIRouter()

_NOT_AVAILABLE = HTTPException(
    status_code=422, detail="Payment plan is not available for this payment method"
)


@router.put(
    "/transactions/{transaction_id}/payment-plan",
    response_model=TransactionOut,
    dependencies=[APP_ONLY],
)
def put_payment_plan(
    transaction_id: int,
    body: PaymentPlanIn,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        transaction = change_payment_plan(conn, transaction_id, body.plan, body.count)
    except TransactionNotFoundError:
        raise HTTPException(status_code=404, detail="Transaction not found") from None
    except PlanNotAvailableError:
        raise _NOT_AVAILABLE from None
    except InvalidPlanCountError:
        raise HTTPException(status_code=422, detail="count is out of range") from None
    return TransactionOut.from_model(transaction)


@router.put(
    "/transactions/{transaction_id}/charges/{seq}/fee",
    response_model=TransactionOut,
    dependencies=[APP_ONLY],
)
def put_charge_fee(
    transaction_id: int,
    seq: int,
    body: FeeIn,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        transaction = set_charge_fee(conn, transaction_id, seq, body.fee)
    except (TransactionNotFoundError, ChargeNotFoundError):
        raise HTTPException(status_code=404, detail="Charge not found") from None
    except FeeNotEditableError:
        raise HTTPException(
            status_code=409, detail="Revolving fees are edited per month"
        ) from None
    except PlanNotAvailableError:
        raise _NOT_AVAILABLE from None
    return TransactionOut.from_model(transaction)


@router.get(
    "/revolving/{payment_method}",
    response_model=list[RevolvingMonthOut],
    dependencies=[APP_ONLY],
)
def get_revolving(
    payment_method: str,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        months = fetch_revolving(conn, payment_method)
    except PlanNotAvailableError:
        raise _NOT_AVAILABLE from None
    return [RevolvingMonthOut.from_model(m) for m in months]


@router.put(
    "/revolving/{payment_method}/months/{month}/fee",
    response_model=list[RevolvingMonthOut],
    dependencies=[APP_ONLY],
)
def put_revolving_fee(
    payment_method: str,
    body: FeeIn,
    month: str = Path(pattern=MONTH_PATTERN),
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        months = set_revolving_fee(conn, payment_method, month, body.fee)
    except PlanNotAvailableError:
        raise _NOT_AVAILABLE from None
    return [RevolvingMonthOut.from_model(m) for m in months]
