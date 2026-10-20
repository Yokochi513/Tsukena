import json
import os
import urllib.error
import urllib.request
from typing import Any

# Discord の HTTP の API（→ docs/adr/0008-record-and-notify-via-owner-dm.md）。
# Gateway には接続しない。常時接続は bot のプロセスだけが持つ
API_BASE_URL = "https://discord.com/api/v10"
# Discord は bot からの呼び出しに、この形の User-Agent を求める
USER_AGENT = "DiscordBot (https://github.com/Yokochi513/Tsukena, 0.1.0)"
# 1回のメッセージに送れる文字数の上限
MAX_CONTENT_LENGTH = 2000
TIMEOUT_SECONDS = 10

# 持ち主との DM のチャンネルの ID。最初に送るときに Discord から取り、プロセスの間は使い回す
_dm_channel_id: str | None = None


class NotifyError(Exception):
    """持ち主に DM を送れなかった"""


def send_dm(text: str) -> None:
    """bot の持ち主に DM を送る（→ docs/design.md 4.4）。

    - 持ち主は Discord のアプリの持ち主とし、設定には持たない
    - 2000文字を超える文面は、行の区切りで分けて複数回に送る
    - 送れなければ NotifyError を投げる。黙って捨てないため
    """
    channel_id = _get_dm_channel_id()
    for chunk in _split(text):
        _request("POST", f"/channels/{channel_id}/messages", {"content": chunk})


def _get_dm_channel_id() -> str:
    global _dm_channel_id
    if _dm_channel_id is None:
        owner_id = _request("GET", "/oauth2/applications/@me")["owner"]["id"]
        channel = _request("POST", "/users/@me/channels", {"recipient_id": owner_id})
        _dm_channel_id = channel["id"]
    return _dm_channel_id


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    req = urllib.request.Request(
        API_BASE_URL + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "Authorization": f"Bot {os.environ['DISCORD_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise NotifyError(f"{method} {path}: {error.code} {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise NotifyError(f"{method} {path}: {error}") from error


def _split(text: str) -> list[str]:
    """上限の文字数ごとに分ける。なるべく行の区切りで分け、1行が長すぎるときだけ行の途中で分ける"""
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > MAX_CONTENT_LENGTH:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:MAX_CONTENT_LENGTH])
            line = line[MAX_CONTENT_LENGTH:]
        if len(current) + len(line) > MAX_CONTENT_LENGTH:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return [c.rstrip("\n") for c in chunks if c.strip()]
