import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ...mail import mail_parser
from ...mail.gmail_client import GmailAuthError, GmailError
from ...repositories.import_failure_repository import (
    fetch_import_failures,
    remove_import_failure,
)
from ...services.importer import ImportFailureNotFoundError, retry_failed_mail
from ..dependencies import APP_ONLY, get_conn
from ..schemas import ImportFailureOut, ImportRetryOut

router = APIRouter()


@router.get(
    "/import-failures",
    response_model=list[ImportFailureOut],
    dependencies=[APP_ONLY],
)
def get_import_failures(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
    return [ImportFailureOut.from_model(f) for f in fetch_import_failures(conn)]


# 失敗の記録を消すと、そのメールは次の取り込みで解析し直される（解析器を直した後の取り込み直し）
@router.delete(
    "/import-failures/{message_id}", status_code=204, dependencies=[APP_ONLY]
)
def delete_import_failure(
    message_id: str,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    with conn:
        deleted = remove_import_failure(conn, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Import failure not found")


# 解析器を直した後に、取り込めなかったメールをその場で取り込み直す
@router.post(
    "/import-failures/{message_id}/retry",
    response_model=ImportRetryOut,
    dependencies=[APP_ONLY],
)
def retry_import_failure(
    message_id: str,
    conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
):
    try:
        recorded = retry_failed_mail(conn, message_id)
    except ImportFailureNotFoundError:
        raise HTTPException(
            status_code=404, detail="Import failure not found"
        ) from None
    except mail_parser.UnparsableMailError as error:
        # 解析器がまだ対応していない。理由をアプリにそのまま見せる
        raise HTTPException(status_code=422, detail=error.reason) from None
    except GmailAuthError:
        raise HTTPException(status_code=503, detail="Gmail is not linked") from None
    except GmailError:
        raise HTTPException(
            status_code=502, detail="Could not fetch the mail from Gmail"
        ) from None
    return ImportRetryOut(recorded=recorded)
