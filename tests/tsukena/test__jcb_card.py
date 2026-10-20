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


# 利用のたびに届く通知（見出しが無く、日時に時刻が付く）。実際のメールの本文で、氏名だけを置き換えている
SAMPLE_REALTIME = """\
山田　太郎 様
カード名称　：　ディズニー★ＪＣＢカード

いつもディズニー★ＪＣＢカードをご利用いただきありがとうございます。
JCBカードのご利用がありましたのでご連絡します。


【ご利用日時(日本時間)】　2026/10/19 09:07
【ご利用金額】　980円
【ご利用先】　グ－グル　プレイ　アツプ

▼ご留意点
　・国内の加盟店の場合、【ご利用先】はすべてカタカナ表示となります。（例：一休→イツキユウ）
　・加盟店から売上到着前の情報のため、利用明細に表示される利用先名称と異なる場合があります。

▼【ご利用先】が「JCBカードご利用分（海外利用分）」でも日本国内利用の場合があります
　・日本国内の利用（インターネット利用含む）でも運営会社が海外の場合、【利用先】「JCBカードご利用分（海外利用分）」
　　と表示されることがあります。

▼会費やサブスクリプションのお支払いでは、カードの利用時でなくても通知される場合があります
　　例）Amazonプライム年会費　5,900円　　→　アマゾン　5,900円

　　※Amazon（アマゾン）のご利用内容は、カード会社では調査できません。
　　　ご自身でAmazonアプリまたは、Amazon.co.jpにログインして確認してください。

▼ご利用に心当たりがない場合
　よくあるご質問「カードを利用していないのに「カードご利用通知」がきた。」をご確認ください。
　【確認方法】
　・トップページから、「トラブル・こんなときは！＞利用の覚えのない請求がある」から確認
　・トップページで「カードご利用通知」と検索

＜注意事項＞
　・本メールは送信専用です。返信されてもお応えできません。
　・本メールの配信停止・Eメールアドレスの変更はMyJCBにログインのうえお手続きください。
　　MyJCBトップ「My安心設定」＞カード利用関連の通知

＜お問い合わせ＞
　株式会社ジェーシービー
　東京都港区南青山5-1-22　青山ライズスクエア
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


def test_利用のたびの通知から利用日時_金額_店名を取り出す():
    # 注意書きの中の【ご利用先】や金額には引きずられない
    assert parse_body(SAMPLE_REALTIME) == [
        Usage(
            occurred_date=datetime.date(2026, 10, 19),
            occurred_time=datetime.time(9, 7),
            amount=980,
            merchant="グ－グル　プレイ　アツプ",
        )
    ]


def test_利用日時の全角の時刻を読む():
    body = "【ご利用日時（日本時間）】　２０２６／１０／１９　２１：３０\n【ご利用金額】　500円\n"
    [usage] = parse_body(body)
    assert usage.occurred_time == datetime.time(21, 30)


def test_利用日時の時刻を読めなければ失敗にする():
    body = "【ご利用日時(日本時間)】　2026/10/19 25:00\n【ご利用金額】　500円\n"
    with pytest.raises(UnparsableMailError) as e:
        parse_body(body)
    assert e.value.reason.startswith("ご利用時刻を読めません")


def test_見出しが無く金額があるのに日付が無ければ失敗にする():
    with pytest.raises(UnparsableMailError) as e:
        parse_body("【ご利用金額】　500円\n")
    assert e.value.reason == "ご利用日が見つかりません"


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
