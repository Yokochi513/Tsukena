import datetime

import pytest

from tsukena.mail.mail_parser.errors import UnparsableMailError
from tsukena.mail.mail_parser.jcb_card import parse_body
from tsukena.mail.mail_parser.usage import Usage

# 実際の利用通知メールの本文。氏名だけを置き換えている
SAMPLE_ONE = """\
山田　太郎 様
カード名称　：　ディズニー★ＪＣＢカード


　◆ご利用１
　　【ご利用日】　2026/10/17
　　【ご利用金額】　 4,959円
　　【ご利用先】　コスモ　　　コセイＳＳ

　※本通知は、カードご利用時に通知していないものが対象です。

▼ショッピング1回払いをご利用の場合、お支払い方法・金額の変更ができます。
→  https://my.jcb.co.jp/DirectLogin?transition_id=1050301&tk_id=myj_edmp_sm1_1
　※一部、利用できないカードおよび加盟店があります。

＜注意事項＞
　・本メールに記載のURLはパソコン・スマートフォンよりご確認ください。
　・本メールは送信専用です。返信されてもお応えできません。
　・本メールの配信停止・Eメールアドレスの変更はMyJCBにログインのうえお手続きください。

＜本件に関するお問い合わせ＞
株式会社ジェーシービー
東京都港区南青山5-1-22　青山ライズスクエア
●お問い合わせ→  https://www.jcb.co.jp/support/index.html
"""


def _block(n: str, date: str, amount: str, merchant: str) -> str:
    return (
        f"　◆ご利用{n}\n"
        f"　　【ご利用日】　{date}\n"
        f"　　【ご利用金額】　 {amount}\n"
        f"　　【ご利用先】　{merchant}\n\n"
    )


def test_1件の通知から利用日_金額_店名を取り出す():
    assert parse_body(SAMPLE_ONE) == [
        Usage(
            occurred_date=datetime.date(2026, 10, 17),
            occurred_time=None,
            amount=4959,
            merchant="コスモ　　　コセイＳＳ",
        )
    ]


def test_複数件の通知は本文の順に取り出す():
    body = "様\n\n" + _block("１", "2026/10/17", "4,959円", "A") + _block(
        "２", "2026/10/18", "120円", "B"
    )
    assert [(u.occurred_date.day, u.amount, u.merchant) for u in parse_body(body)] == [
        (17, 4959, "A"),
        (18, 120, "B"),
    ]


def test_全角の数字の日付と金額を読む():
    body = _block("１", "２０２６／１０／１７", "１，２００円", "店")
    [usage] = parse_body(body)
    assert usage.occurred_date == datetime.date(2026, 10, 17)
    assert usage.amount == 1200


def test_ご利用先が無ければ店名は空文字():
    body = "　◆ご利用１\n　　【ご利用日】　2026/10/17\n　　【ご利用金額】　 500円\n"
    assert parse_body(body)[0].merchant == ""


def test_利用の見出しが無ければ空のリスト():
    assert parse_body("お知らせ\nキャンペーンのご案内です。\n") == []


@pytest.mark.parametrize(
    ("date", "amount", "reason"),
    [
        ("2026/13/01", "500円", "ご利用日を読めません"),
        ("2026/10/17", "-500円", "ご利用金額を読めません"),
        ("2026/10/17", "0円", "ご利用金額を読めません"),
    ],
)
def test_日付と金額を読めなければ失敗にする(date: str, amount: str, reason: str):
    with pytest.raises(UnparsableMailError) as e:
        parse_body(_block("１", date, amount, "店"))
    assert e.value.reason.startswith(reason)


def test_1件でも読めない支払いがあればメール全体を失敗にする():
    body = _block("１", "2026/10/17", "500円", "A") + "　◆ご利用２\n　　【ご利用先】　B\n"
    with pytest.raises(UnparsableMailError) as e:
        parse_body(body)
    assert e.value.reason == "ご利用日が見つかりません"
