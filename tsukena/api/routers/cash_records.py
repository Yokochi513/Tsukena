import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response

from ...model.enum.record_outcome import RecordOutcome
from ...services.transaction_service import UnparsableMessageError, record_cash
from ..dependencies import BOT_ONLY, get_conn
from ..schemas import CashRecordIn, RecordResultOut

router = APIRouter()


@router.post(
    "/cash-records",
    response_model=RecordResultOut,
    status_code=201,
    dependencies=[BOT_ONLY],
)
def post_cash_record(
    body: CashRecordIn,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        result = record_cash(conn, body.text, body.message_id, body.sent_at)
    except UnparsableMessageError:
        raise HTTPException(status_code=400, detail="unparsable") from None
    # 記録しなかった（重複・削除済み）ときは、新しく作っていないので 200 にする
    if result.outcome is not RecordOutcome.RECORDED:
        response.status_code = 200
    return RecordResultOut.from_model(result)
