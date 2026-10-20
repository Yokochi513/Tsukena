import datetime

import pytest

from tsukena.mail import mail_parser
from tsukena.model.enum.source import Source
from tsukena.model.mail_message_model import MailMessage
from tsukena.model.parsed_payment_model import ParsedPayment

from .test__jcb_card import SAMPLE_ONE

JCB_SENDER = "JCB Webmaster <mail@qa.jcb.co.jp>"


def test_送り主で解析器を選び_支払い手段と重複排除キーを付ける():
    mail = MailMessage("abc123", JCB_SENDER, "カードご利用のお知らせ", SAMPLE_ONE)
    assert mail_parser.parse(mail) == [
        ParsedPayment(
            occurred_date=datetime.date(2026, 10, 17),
            occurred_time=None,
            amount=4959,
            merchant="コスモ　　　コセイＳＳ",
            payment_method="JCBカード",
            source=Source.GMAIL,
            source_ref="gmail:abc123:0",
        )
    ]


def test_送り主のアドレスは大文字と小文字を区別しない():
    mail = MailMessage("abc123", "JCB <MAIL@QA.JCB.CO.JP>", "", SAMPLE_ONE)
    assert mail_parser.parse(mail)[0].payment_method == "JCBカード"


def test_登録されていない送り主は失敗にする():
    mail = MailMessage("abc123", "知らない <someone@example.com>", "", SAMPLE_ONE)
    with pytest.raises(mail_parser.UnparsableMailError) as e:
        mail_parser.parse(mail)
    assert e.value.reason == "登録されていない送り主です"


def test_支払いが1件も無ければ失敗にする():
    mail = MailMessage("abc123", JCB_SENDER, "お知らせ", "キャンペーンのご案内です。")
    with pytest.raises(mail_parser.UnparsableMailError) as e:
        mail_parser.parse(mail)
    assert e.value.reason == "支払いが見つかりません"


def test_登録表の支払い手段を返す():
    assert "JCBカード" in mail_parser.payment_methods()
