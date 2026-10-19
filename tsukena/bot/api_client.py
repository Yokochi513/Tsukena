import datetime
from types import TracebackType
from typing import Any, Self

import aiohttp

from ..model.category_model import Category
from ..model.enum.record_outcome import RecordOutcome
from ..model.enum.source import Source
from ..model.enum.status import Status
from ..model.record_model import RecordResult
from ..model.transaction_model import Transaction
from ..normalize import normalize

# API のプロセスが止まっているときに、返事を待たせすぎないための上限（秒）
TIMEOUT_SECONDS = 10


class ApiError(Exception):
    """API に接続できない、または想定していない応答が返ったときに送出する。"""


class ApiClient:
    """bot から REST API を呼び、JSON と model の構造を相互に変換する（→ ADR-0007）。

    接続（aiohttp のセッション）はイベントループの中で作る必要があるため、
    `async with ApiClient(...) as api:` の中で使う。
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        self._session = aiohttp.ClientSession(
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def record_cash(
        self, text: str, message_id: int, sent_at: datetime.datetime
    ) -> RecordResult | None:
        """POST /cash-records を呼ぶ。本文を分解できなかった（400）ときは None を返す。"""
        body = {
            "text": text,
            "message_id": str(message_id),
            "sent_at": sent_at.isoformat(),
        }
        status, data = await self._request("POST", "/cash-records", json=body)
        if status == 400:
            return None
        self._expect(status, (200, 201), "POST /cash-records")
        return _to_record_result(data, message_id)

    async def fetch_categories(self) -> list[Category]:
        """GET /categories を呼ぶ。表示順の小さい順、同じなら ID の小さい順に返る。"""
        status, data = await self._request("GET", "/categories")
        self._expect(status, (200,), "GET /categories")
        return [_to_category(c) for c in data]

    async def find_transaction_id_by_source_ref(self, source_ref: str) -> int | None:
        """GET /transactions?source_ref= を呼ぶ。見つからなければ None を返す。"""
        status, data = await self._request(
            "GET", "/transactions", params={"source_ref": source_ref}
        )
        self._expect(status, (200,), "GET /transactions")
        return data[0]["id"] if data else None

    async def select_category(self, transaction_id: int, category_id: int) -> bool:
        """PATCH /transactions/{id} にカテゴリだけを送る。記録が無い（404）ときは False を返す。"""
        path = f"/transactions/{transaction_id}"
        status, _ = await self._request(
            "PATCH", path, json={"category_id": category_id}
        )
        if status == 404:
            return False
        self._expect(status, (200,), f"PATCH {path}")
        return True

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> tuple[int, Any]:
        if self._session is None:
            raise RuntimeError("ApiClient は async with の中で使ってください")
        try:
            async with self._session.request(
                method, self._base_url + path, **kwargs
            ) as response:
                data = (
                    await response.json()
                    if response.content_type == "application/json"
                    else None
                )
                return response.status, data
        except (aiohttp.ClientError, TimeoutError) as e:
            raise ApiError(f"{method} {path} に接続できませんでした: {e}") from e

    @staticmethod
    def _expect(status: int, expected: tuple[int, ...], label: str) -> None:
        if status not in expected:
            raise ApiError(f"{label} が想定していない応答を返しました: {status}")


def _to_category(data: dict[str, Any]) -> Category:
    return Category(
        id=data["id"],
        name=data["name"],
        emoji=data["emoji"],
        sort_order=data["sort_order"],
    )


def _to_transaction(data: dict[str, Any], message_id: int) -> Transaction:
    t = data["occurred_time"]
    return Transaction(
        id=data["id"],
        occurred_date=datetime.date.fromisoformat(data["occurred_date"]),
        occurred_time=datetime.time.fromisoformat(t) if t is not None else None,
        paid_date=datetime.date.fromisoformat(data["paid_date"]),
        amount=data["amount"],
        merchant=data["merchant"],
        # 照合キーと重複排除キーは API が返さない（サーバーの内部でだけ使う）ため、同じ規則で作り直す
        merchant_key=normalize(data["merchant"]),
        category_id=data["category_id"],
        status=Status(data["status"]),
        payment_method=data["payment_method"],
        source=Source(data["source"]),
        source_ref=f"{Source.DISCORD}:{message_id}",
        created_at=datetime.datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.datetime.fromisoformat(data["updated_at"]),
    )


def _to_record_result(data: dict[str, Any], message_id: int) -> RecordResult:
    t = data["transaction"]
    c = data["category"]
    return RecordResult(
        outcome=RecordOutcome(data["outcome"]),
        transaction=_to_transaction(t, message_id) if t is not None else None,
        category=_to_category(c) if c is not None else None,
    )
