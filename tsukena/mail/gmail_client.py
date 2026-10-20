import base64
import os
from collections.abc import Generator
from contextlib import contextmanager
from email.message import Message
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient import errors
from googleapiclient.discovery import build
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from ..model.mail_message_model import MailMessage

# Gmail のスコープはラベル単位に絞れないため、読み取り専用にする（→ docs/design.md 11）。
# 変更する場合は、token.json を消して連携をやり直す
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# 起動したときのカレントディレクトリによらず、リポジトリの直下の creds/ を見る
CREDS_DIR = Path(__file__).resolve().parents[2] / "creds"
# Google Cloud で作った OAuth クライアント（種類は「ウェブ アプリケーション」）の JSON
CLIENT_SECRETS_PATH = CREDS_DIR / "credentials.json"
# 連携で受け取った認証情報（リフレッシュトークンを含む）
TOKEN_PATH = CREDS_DIR / "token.json"


class GmailError(Exception):
    """Gmail からメールを取れなかった。次の周期でやり直せばよい"""


class GmailAuthError(GmailError):
    """連携が切れている。持ち主に Gmail 連携をやり直してもらう必要がある"""


def list_message_ids(query: str) -> list[str]:
    """検索条件（Gmail の検索演算子）に合うメールの ID を、すべてのページから集めて返す。"""
    ids: list[str] = []
    page_token: str | None = None
    with _translate_errors():
        messages = _service().users().messages()
        while True:
            res = messages.list(userId="me", q=query, pageToken=page_token).execute()
            ids += [m["id"] for m in res.get("messages", [])]
            page_token = res.get("nextPageToken")
            if page_token is None:
                return ids


def get_message(message_id: str) -> MailMessage:
    """メール1通を取り出す。件名・テキストの本文が無ければ空文字にする。"""
    with _translate_errors():
        detail = _service().users().messages().get(userId="me", id=message_id).execute()
    payload = detail["payload"]
    return MailMessage(
        message_id=message_id,
        sender=_header(payload["headers"], "From"),
        subject=_header(payload["headers"], "Subject"),
        body=_text_body(payload),
    )


def load_credentials() -> Credentials:
    """保存済みの認証情報を読む。期限が切れていれば更新して保存し直す。

    - 認証情報が無い、または更新できなければ GmailAuthError を投げる
    - 同意画面を開く流れは持たない。連携は /oauth/google/callback が行う（→ docs/api_list.md 2.7）
    """
    if not TOKEN_PATH.exists():
        raise GmailAuthError("Gmail と連携していません")
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.valid:
        return creds
    if not creds.refresh_token:
        raise GmailAuthError("認証情報を更新できません")
    try:
        creds.refresh(Request())
    except RefreshError as error:
        raise GmailAuthError(str(error)) from error
    _save_token(creds.to_json())
    return creds


def start_authorization(redirect_uri: str) -> tuple[str, str, str]:
    """Google の同意画面の URL を作る（→ docs/api_list.md 2.7）。

    URL・state・PKCE の code_verifier を返す。state と code_verifier は、連携を終えるときまで呼び出す側が持つ。
    """
    flow = _flow(redirect_uri)
    # リフレッシュトークンを必ず受け取るため、オフラインのアクセスを求め、同意画面を毎回出す
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    assert flow.code_verifier is not None
    return url, state, flow.code_verifier


def finish_authorization(redirect_uri: str, code: str, code_verifier: str) -> None:
    """認可コードを認証情報に交換し、保存する。既に連携済みなら上書きする。

    交換できなければ GmailAuthError を投げ、認証情報は保存しない。
    """
    flow = _flow(redirect_uri, code_verifier)
    try:
        flow.fetch_token(code=code)
    except OAuth2Error as error:
        raise GmailAuthError(str(error)) from error
    creds = flow.credentials
    if not creds.refresh_token:
        # 無いと1時間後に更新できず、連携が切れる
        raise GmailAuthError("リフレッシュトークンを受け取れませんでした")
    _save_token(creds.to_json())


def _flow(redirect_uri: str, code_verifier: str | None = None) -> Flow:
    if not CLIENT_SECRETS_PATH.exists():
        raise GmailAuthError(f"{CLIENT_SECRETS_PATH.name} がありません")
    return Flow.from_client_secrets_file(
        str(CLIENT_SECRETS_PATH),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
        autogenerate_code_verifier=code_verifier is None,
    )


def _save_token(token_json: str) -> None:
    # リフレッシュトークンは Gmail を読める鍵なので、持ち主だけが読めるようにする（→ docs/design.md 9）。
    # Windows では権限の指定は効かない
    TOKEN_PATH.parent.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token_json)
    os.chmod(TOKEN_PATH, 0o600)


@contextmanager
def _translate_errors() -> Generator[None]:
    """Google のライブラリの例外を、importer が知っている例外に置き換える"""
    try:
        yield
    except errors.HttpError as error:
        if error.status_code in (401, 403):
            raise GmailAuthError(str(error)) from error
        raise GmailError(str(error)) from error
    except RefreshError as error:
        raise GmailAuthError(str(error)) from error


def _service() -> Any:
    return build("gmail", "v1", credentials=load_credentials(), cache_discovery=False)


def _header(headers: list[dict[str, str]], name: str) -> str:
    """ヘッダーの値を返す。無ければ空文字。ヘッダー名の大文字・小文字は区別しない"""
    return next((h["value"] for h in headers if h["name"].lower() == name.lower()), "")


def _text_body(part: dict[str, Any]) -> str:
    """マルチパートをたどり、最初に見つかった text/plain の本文を返す。無ければ空文字"""
    if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
        data = base64.urlsafe_b64decode(part["body"]["data"])
        return _decode(data, _header(part.get("headers", []), "Content-Type"))
    for child in part.get("parts", []):
        body = _text_body(child)
        if body != "":
            return body
    return ""


def _decode(data: bytes, content_type: str) -> str:
    # Gmail API は転送用の符号化（Base64 など）を解くだけで、文字コードは送られたまま返す。
    # 日本のカード会社のメールは ISO-2022-JP のことがあるため、Content-Type の charset に従う
    msg = Message()
    msg["Content-Type"] = content_type or "text/plain"
    charset = msg.get_content_charset() or "utf-8"
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        # Python が知らない charset の名前が書かれていた
        return data.decode("utf-8", errors="replace")
