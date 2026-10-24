import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from google.auth.exceptions import TransportError

from ...mail import gmail_client
from ...mail.gmail_client import GmailAuthError
from ..dependencies import APP_ONLY
from ..html import html_page
from ..oauth_state import OAuthStateStore
from ..schemas import GoogleAuthStartOut, GoogleAuthStatusOut

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/oauth/google/start",
    response_model=GoogleAuthStartOut,
    dependencies=[APP_ONLY],
)
def start_google_auth(request: Request):
    google_redirect_uri: str | None = request.app.state.google_redirect_uri
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
    oauth_states: OAuthStateStore = request.app.state.oauth_states
    oauth_states.put(state, code_verifier)
    return GoogleAuthStartOut(authorization_url=url)


# 取り込みと同じく認証情報を読めるか（期限切れなら更新できるか）で確かめる（→ docs/api_list.md 2.7）
@router.get(
    "/oauth/google/status",
    response_model=GoogleAuthStatusOut,
    dependencies=[APP_ONLY],
)
def get_google_auth_status():
    try:
        gmail_client.load_credentials()
    except GmailAuthError:
        return GoogleAuthStatusOut(linked=False)
    except TransportError:
        # 更新のために Google へつなげなかった。切れているかどうかは分からない
        raise HTTPException(status_code=502, detail="Could not reach Google") from None
    return GoogleAuthStatusOut(linked=True)


# Google からのリダイレクトでブラウザが呼ぶため、トークンを求めず state で確かめる（→ docs/api_list.md 2.7）
@router.get("/oauth/google/callback", response_class=HTMLResponse)
def google_auth_callback(
    request: Request,
    state: str = "",
    code: str | None = None,
    error: str | None = None,
):
    oauth_states: OAuthStateStore = request.app.state.oauth_states
    code_verifier = oauth_states.pop(state)
    if code_verifier is None:
        return html_page(
            "連携できませんでした",
            "リンクの有効期限が切れたか、既に使われています。アプリから連携をやり直してください。",
            status_code=400,
        )
    if error is not None or code is None:
        # 同意画面で「キャンセル」を選んだ
        return html_page(
            "連携しませんでした",
            "Gmail との連携は行われませんでした。ブラウザの「戻る」でアプリに戻ってください。",
        )
    google_redirect_uri: str | None = request.app.state.google_redirect_uri
    assert google_redirect_uri is not None
    try:
        gmail_client.finish_authorization(google_redirect_uri, code, code_verifier)
    except GmailAuthError:
        logger.warning("Gmail の認証情報を受け取れませんでした", exc_info=True)
        return html_page(
            "連携できませんでした",
            "Google から認証情報を受け取れませんでした。アプリから連携をやり直してください。",
            status_code=400,
        )
    return html_page(
        "連携しました",
        # アプリの Web 版は同意画面を同じタブで開くため、「戻る」でアプリに戻れる
        "Gmail との連携が完了しました。ブラウザの「戻る」でアプリに戻ってください。",
    )
