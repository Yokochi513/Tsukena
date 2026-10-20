import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

# 同意画面を開いてから戻ってくるまでに待つ時間（→ docs/api_list.md 2.7）
STATE_TTL_SECONDS = 10 * 60


@dataclass(frozen=True)
class _Entry:
    code_verifier: str
    expires_at: float


class OAuthStateStore:
    """Gmail 連携の state を、連携が終わるまでの間だけ覚えておく。

    プロセスのメモリに持つ。再起動すれば消えるが、そのときは連携を始めからやり直せばよい。
    """

    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._entries: dict[str, _Entry] = {}
        # エンドポイントは別々のスレッドで動くことがあるため
        self._lock = threading.Lock()

    def put(self, state: str, code_verifier: str) -> None:
        with self._lock:
            self._drop_expired()
            self._entries[state] = _Entry(code_verifier, self._now() + STATE_TTL_SECONDS)

    def pop(self, state: str) -> str | None:
        """state に対応する code_verifier を返し、その state を捨てる。

        知らない state・期限切れの state・2回目の呼び出しでは None を返す。
        """
        with self._lock:
            self._drop_expired()
            for known in list(self._entries):
                # 推測されにくいよう、文字列の比較の時間を一定にする
                if secrets.compare_digest(known, state):
                    return self._entries.pop(known).code_verifier
            return None

    def _drop_expired(self) -> None:
        now = self._now()
        for state in [s for s, e in self._entries.items() if e.expires_at <= now]:
            del self._entries[state]
