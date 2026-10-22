import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..mail import gmail_client, mail_parser
from ..mail.gmail_client import GmailAuthError, GmailError
from ..model.api_tokens import ApiTokens
from ..model.enum.record_outcome import RecordOutcome
from ..model.enum.status import Status
from ..repositories.category_repository import (
    DuplicateCategoryError,
    fetch_categories,
    insert_category,
    update_category,
)
from ..repositories.database import connect
from ..repositories.import_failure_repository import (
    fetch_import_failures,
    remove_import_failure,
)
from ..repositories.income_repository import (
    fetch_incomes,
    insert_income,
    remove_income,
    update_income,
)
from ..repositories.setting_repository import fetch_setting, update_monthly_budget
from ..repositories.summary_repository import fetch_monthly_summary
from ..repositories.transaction_repository import fetch_transactions, remove_transaction
from ..services.importer import ImportFailureNotFoundError, retry_failed_mail
from ..services.transaction_service import (
    CategoryNotFoundError,
    InvalidPaidDateError,
    TransactionNotFoundError,
    UnparsableMessageError,
    modify_transaction,
    record_cash,
)
from .auth import Caller, allow
from .oauth_state import OAuthStateStore
from .schemas import (
    BudgetIn,
    BudgetOut,
    CashRecordIn,
    CategoryIn,
    CategoryOut,
    GoogleAuthStartOut,
    ImportFailureOut,
    ImportRetryOut,
    IncomeIn,
    IncomeOut,
    MonthlySummaryOut,
    RecordResultOut,
    TransactionOut,
    TransactionUpdateIn,
)

logger = logging.getLogger(__name__)

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
APP_ONLY = Depends(allow(Caller.APP))
APP_OR_BOT = Depends(allow(Caller.APP, Caller.BOT))
BOT_ONLY = Depends(allow(Caller.BOT))


def create_app(
    db_path: Path,
    api_tokens: ApiTokens,
    cors_origins: list[str] | None = None,
    google_redirect_uri: str | None = None,
) -> FastAPI:
    """google_redirect_uri が無ければ、Gmail 連携のエンドポイントは 503 を返す"""
    app = FastAPI(title="Tsukena API")
    app.state.db_path = db_path
    app.state.api_tokens = api_tokens
    oauth_states = OAuthStateStore()

    # Flutter Web の開発サーバーはポートが毎回変わるため、ローカルのオリジンをポート問わず許可する
    app.add_middleware(
        CORSMiddleware,
        # 本番の Web 版（GitHub Pages）は API と別のオリジンなので、設定に書いたオリジンを許可する（→ ADR-0010）
        allow_origins=cors_origins or [],
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        # Authorization はブラウザが既定では許さないヘッダーなので、明示しないとプリフライトで断られる
        allow_headers=["Authorization", "Content-Type"],
    )

    # 外から URL だけを見に来た人（セキュリティ製品の審査を含む）に、何のサーバーかを示す（→ docs/api_list.md 2.9）
    @app.get("/", response_class=HTMLResponse)
    def index():
        return _html_page(
            "このサーバーについて",
            "Tsukena は、個人が自分ひとりで使う家計簿アプリのサーバー（API）です。"
            "スマホアプリと Discord の bot だけが、トークンを付けて呼び出します。"
            "利用者の登録や、外部の方が使える機能はありません。",
        )

    # 記録も収入も無い月や来月以降の月でも 404 にせず、合計を0で返す（→ docs/api_list.md 2.1）
    @app.get(
        "/months/{month}/summary",
        response_model=MonthlySummaryOut,
        dependencies=[APP_ONLY],
    )
    def get_monthly_summary(
        month: str = PathParam(pattern=MONTH_PATTERN),
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        return MonthlySummaryOut.from_model(fetch_monthly_summary(conn, month))

    @app.get(
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

    @app.patch(
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

    @app.delete(
        "/transactions/{transaction_id}", status_code=204, dependencies=[APP_ONLY]
    )
    def delete_transaction(
        transaction_id: int,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        if not remove_transaction(conn, transaction_id):
            raise HTTPException(status_code=404, detail="Transaction not found")

    @app.get("/incomes", response_model=list[IncomeOut], dependencies=[APP_ONLY])
    def get_incomes(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [IncomeOut.from_model(income) for income in fetch_incomes(conn)]

    @app.post(
        "/incomes", response_model=IncomeOut, status_code=201, dependencies=[APP_ONLY]
    )
    def post_income(
        body: IncomeIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        return IncomeOut.from_model(insert_income(conn, body.to_model()))

    @app.patch(
        "/incomes/{income_id}", response_model=IncomeOut, dependencies=[APP_ONLY]
    )
    def patch_income(
        income_id: int,
        body: IncomeIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        income = update_income(conn, income_id, body.to_model())

        if income is None:
            raise HTTPException(status_code=404, detail="Income not found")
        return IncomeOut.from_model(income)

    @app.delete("/incomes/{income_id}", status_code=204, dependencies=[APP_ONLY])
    def delete_income(income_id: int, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        if not remove_income(conn, income_id):
            raise HTTPException(status_code=404, detail="Income not found")

    @app.get("/categories", response_model=list[CategoryOut], dependencies=[APP_OR_BOT])
    def get_categories(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [CategoryOut.from_model(category) for category in fetch_categories(conn)]

    @app.post(
        "/categories",
        response_model=CategoryOut,
        status_code=201,
        dependencies=[APP_ONLY],
    )
    def post_category(body: CategoryIn, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        try:
            category = insert_category(conn, body.to_model())
        except DuplicateCategoryError:
            raise HTTPException(
                status_code=422, detail="Category name or emoji already exists"
            ) from None
        return CategoryOut.from_model(category)

    @app.patch(
        "/categories/{category_id}", response_model=CategoryOut, dependencies=[APP_ONLY]
    )
    def patch_category(
        category_id: int,
        body: CategoryIn,
        conn: sqlite3.Connection = Depends(get_conn),  # noqa: B008
    ):
        try:
            category = update_category(conn, category_id, body.to_model())
        except DuplicateCategoryError:
            raise HTTPException(
                status_code=422, detail="Category name or emoji already exists"
            ) from None

        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return CategoryOut.from_model(category)

    @app.get("/budget", response_model=BudgetOut, dependencies=[APP_ONLY])
    def get_budget(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return BudgetOut(monthly_budget=fetch_setting(conn).monthly_budget)

    # 予算は全体で1つだけ持つ。変えると過去の月の集計もこの値で計算される（→ docs/api_list.md 2.5）
    @app.put("/budget", response_model=BudgetOut, dependencies=[APP_ONLY])
    def put_budget(body: BudgetIn, conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        update_monthly_budget(conn, body.monthly_budget)
        return BudgetOut(monthly_budget=fetch_setting(conn).monthly_budget)

    @app.post(
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

    @app.get(
        "/import-failures",
        response_model=list[ImportFailureOut],
        dependencies=[APP_ONLY],
    )
    def get_import_failures(conn: sqlite3.Connection = Depends(get_conn)):  # noqa: B008
        return [ImportFailureOut.from_model(f) for f in fetch_import_failures(conn)]

    # 失敗の記録を消すと、そのメールは次の取り込みで解析し直される（解析器を直した後の取り込み直し）
    @app.delete(
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
    @app.post(
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

    @app.get(
        "/oauth/google/start",
        response_model=GoogleAuthStartOut,
        dependencies=[APP_ONLY],
    )
    def start_google_auth():
        if google_redirect_uri is None:
            raise HTTPException(status_code=503, detail="Gmail link is not configured")
        try:
            url, state, code_verifier = gmail_client.start_authorization(
                google_redirect_uri
            )
        except GmailAuthError:
            # credentials.json が置かれていない
            raise HTTPException(
                status_code=503, detail="Gmail link is not configured"
            ) from None
        oauth_states.put(state, code_verifier)
        return GoogleAuthStartOut(authorization_url=url)

    # Google からのリダイレクトでブラウザが呼ぶため、トークンを求めず state で確かめる（→ docs/api_list.md 2.7）
    @app.get("/oauth/google/callback", response_class=HTMLResponse)
    def google_auth_callback(
        state: str = "",
        code: str | None = None,
        error: str | None = None,
    ):
        code_verifier = oauth_states.pop(state)
        if code_verifier is None:
            return _html_page(
                "連携できませんでした",
                "リンクの有効期限が切れたか、既に使われています。アプリから連携をやり直してください。",
                status_code=400,
            )
        if error is not None or code is None:
            # 同意画面で「キャンセル」を選んだ
            return _html_page(
                "連携しませんでした",
                "Gmail との連携は行われませんでした。ブラウザの「戻る」でアプリに戻ってください。",
            )
        assert google_redirect_uri is not None
        try:
            gmail_client.finish_authorization(google_redirect_uri, code, code_verifier)
        except GmailAuthError:
            logger.warning("Gmail の認証情報を受け取れませんでした", exc_info=True)
            return _html_page(
                "連携できませんでした",
                "Google から認証情報を受け取れませんでした。アプリから連携をやり直してください。",
                status_code=400,
            )
        return _html_page(
            "連携しました",
            # アプリの Web 版は同意画面を同じタブで開くため、「戻る」でアプリに戻れる
            "Gmail との連携が完了しました。ブラウザの「戻る」でアプリに戻ってください。",
        )

    return app


def _html_page(title: str, message: str, status_code: int = 200) -> HTMLResponse:
    # 文言はすべてこのファイルで決めたもので、外から受け取った値は入れない
    return HTMLResponse(
        f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Tsukena</title>
</head>
<body style="font-family: sans-serif; max-width: 32rem; margin: 3rem auto; padding: 0 1rem;">
<h1>{title}</h1>
<p>{message}</p>
</body>
</html>
""",
        status_code=status_code,
    )


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
