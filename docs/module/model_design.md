# tsukena/model.py

<!-- 見出しは実装先のファイル名（またはモジュール名）。表記は採用言語の慣習に従う -->

## 背景・目的
<!-- なんのために必要なのか -->
Tsukena では、1件の支払いを複数のモジュールが順に受け渡して記録する。
メールの支払いはメールの解析（`mail_parser`）と取り込み（`importer`）を経て記録（`recorder`）に渡り、現金の支払いは Discord の bot（`discord_bot`）から記録に渡る。
記録した結果は、bot の返事、予算の通知、週と月のまとめ、スマホアプリ向けの API がそれぞれ読む。

受け渡す値の形をモジュールごとに決めると、約束が少しずつずれる。
金額を整数で持つか、時刻が分からないときに何を入れるか、確定の記録にカテゴリが無くてよいか、といった約束である。
各モジュールの単体テストはそのモジュールの約束を前提に書かれるため、ずれはテストでは見つからず、モジュールをつないで動かしたときに初めて分かる。
そこで、受け渡すデータ構造と、その値が満たす不変条件を本モジュールの1箇所に定義し、各モジュールの設計書とテストはこれを参照する。

本モジュールは**データの形だけ**を定義する。
カテゴリをどう決めるか、金額をどう取り出すか、予算の閾値をいくつにするかといった判定の規則は持たず、判定するモジュール（`classifier` / `mail_parser` / `cash_parser` / `budget` など）の設計書に置く。

## データ構造一覧
<!-- どのようなデータ構造があるのか -->
| 構造名              | 単位                                         | 概要                                                                     |
| ------------------- | -------------------------------------------- | ------------------------------------------------------------------------ |
| `Status`            | 記録の状態1つ                                | 確定（`confirmed`）／確認待ち（`pending`）の列挙                          |
| `Source`            | 記録の入口1つ                                | Gmail（`gmail`）／Discord（`discord`）の列挙                              |
| `RecordOutcome`     | 1件の記録の試みの結果1つ                     | 保存した／重複で保存しなかった／削除済みで保存しなかった、の列挙         |
| `MailMessage`       | Gmail のメール1通                            | メールの ID・送り主・件名・本文                                          |
| `PaymentTiming`     | 支払い手段の支払い方1つ                      | 即時（`immediate`）／締めてから引き落とす（`card`）の列挙                 |
| `PaymentRule`       | 支払い手段1つの締め日のルール                | 支払い手段・支払い方・締め日・引き落とし日・何か月後に引き落とすか        |
| `ParsedPayment`     | 記録する前の支払い1件                        | 利用日・時刻・金額・店名・支払い手段・入口・重複排除キー                 |
| `CashEntry`         | Discord のメッセージ1件を分解した結果        | メモと金額                                                               |
| `Classification`    | 1件の支払いに対する分類の結果                | 照合キー・カテゴリ・状態                                                 |
| `MerchantRule`      | 分類ルール1つ（照合キー1つ）                 | 照合キーとカテゴリの対応                                                 |
| `Category`          | カテゴリ1つ                                  | 名前・絵文字・表示順                                                     |
| `CategoryUpdate`    | カテゴリ1つに対する変更の指示                | 名前・絵文字・表示順のうち変えるもの                                     |
| `Transaction`       | 保存済みの記録1件                            | `transactions` テーブルの1行と同じ項目                                   |
| `TransactionUpdate` | 記録1件に対する修正の指示                    | 利用日・支払日・金額・店名・カテゴリのうち変えるもの                     |
| `IncomeInput`         | 保存する前の収入1件                          | 入金日・金額・メモ                                                       |
| `Income`            | 保存済みの収入1件                            | `incomes` テーブルの1行と同じ項目                                        |
| `IncomeUpdate`      | 収入1件に対する修正の指示                    | 入金日・金額・メモのうち変えるもの                                       |
| `RecordResult`      | 1件の記録の試み                              | 記録の結果、保存した記録、カテゴリ、その月の予算の状況                   |
| `BudgetStatus`      | 1つの月の予算の状況                          | 予算・支出合計・残り・新たに超えた閾値                                   |
| `CategoryTotal`     | 1つの期間の、カテゴリ1つ分の支出合計         | カテゴリ（未分類なら無し）と金額                                         |
| `MonthlySummary`    | 1つの月の集計                                | 収入合計・支出合計・収支・予算・残り・カテゴリ別の内訳                   |
| `WeeklySummary`     | 1つの週（月曜〜日曜）の集計                  | 週の支出合計・カテゴリ別の内訳・今月の予算の残り・確認待ちの件数         |
| `Settings`          | サーバーの設定一式                           | 月の予算・記録用チャンネル・自分の Discord ユーザー・Gmail ラベル名       |
| `ImportFailure`     | 取り込めなかったメール1通                    | メールの ID・送り主・件名・理由・日時                                    |
| `NotificationLog`   | 送った通知1回（種類と対象期間の組1つ）       | 通知の種類・対象期間・送った日時                                         |

<!-- 「単位」は必ず埋める。この単位が比較・集計・出力の分母になる -->

モジュール間の受け渡しとの対応は次のとおり。

| 受け渡し                                                     | 使う構造                                                 |
| ------------------------------------------------------------ | -------------------------------------------------------- |
| メールの取得（`gmail_client` → `importer` → `mail_parser`）   | `MailMessage`                                            |
| メールの解析結果（`mail_parser` → `importer` → `recorder`）   | `ParsedPayment` の列                                     |
| 現金のメッセージの解析結果（`cash_parser` → `discord_bot`）   | `CashEntry`                                              |
| 現金の記録（`discord_bot` → `recorder`）                      | `ParsedPayment`                                          |
| 分類（`classifier` → `recorder`）                            | `Classification`                                         |
| 支払日の計算（`config` → `recorder` → `paid_date`）          | `PaymentRule`                                            |
| 記録の結果（`recorder` → `importer` / `discord_bot`）        | `RecordResult`（`Transaction` / `Category` / `BudgetStatus` を含む） |
| 予算の計算（`budget` → `recorder`）                          | `BudgetStatus`                                           |
| 集計とまとめ（`repository` / `reporter` → `summary`、`repository` → `api`） | `MonthlySummary` / `WeeklySummary` / `CategoryTotal`     |
| 取り込みの失敗（`importer` → `repository` / `summary`）      | `ImportFailure`                                          |
| アプリからの修正（`api` → サービス層・`repository`）         | `TransactionUpdate` / `CategoryUpdate`                   |
| アプリからの収入の追加・修正（`api` → `repository`）         | `IncomeInput` / `IncomeUpdate`                             |
| 永続化（`repository` ↔ 各モジュール）                        | `Transaction` / `Income` / `Category` / `MerchantRule` / `Settings` / `ImportFailure` / `NotificationLog` |


## 依存関係
<!-- なんのモジュールに依存しているのか -->
| モジュール    | 用途                                                       |
| ------------- | ---------------------------------------------------------- |
| `dataclasses` | 不変のデータ構造の定義（標準ライブラリ）                   |
| `enum`        | 状態・入口・記録の結果・支払い方の列挙（`StrEnum`）（標準ライブラリ） |
| `datetime`    | 日付・時刻・日時の型（標準ライブラリ）                     |

本モジュールは、すべてのモジュールから参照される（→ [design.md 6. 依存の向き](../design.md#6-依存の向き)）。
そのため `tsukena` の他のモジュールには `config` も含めて依存せず、外部ライブラリも持ち込まない。
どれか1つに依存すると、そのモジュールから本モジュールへの参照と合わせて循環が生じるためである。
純粋ロジックのモジュール（`cash_parser` / `mail_parser` / `paid_date` / `budget` / `summary` など）を、外部ライブラリなしで単体テストできるようにする狙いもある。

REST API の入出力の形（`FastAPI` のスキーマ）は本モジュールに置かず、API 側（`api`）で本モジュールの構造との間で変換する。
本モジュールの構造を API の入出力にそのまま使うと、API の項目名やバリデーションの都合を変えるたびに、モジュール間の約束も変わってしまうためである。


## データ構造詳細
<!-- 各データ構造はどのような項目を持つのか -->

全体に共通する約束。

- データ構造は、生成後に書き換えない不変の構造（`@dataclass(frozen=True)`）として定義する。値を変えるときは新しい構造を作る。
- 列挙は文字列の列挙（`StrEnum`）として定義し、値は DB に保存する文字列（[design.md 9. データモデル](../design.md#9-データモデル)）と一致させる。
- 複数の要素を持つフィールドは、書き換えられない列（`tuple`）で持つ。
- 必須の列が「-」のフィールドだけが、値が無いことを `None` で表す。文字列の値が無い場合は空文字を入れ、`None` を使わない（`merchant` など。DB で空文字とする列と揃える）。
- 金額はすべて円単位の整数（`int`）で持つ。浮動小数点は使わない。
- 日付（`date`）と時刻（`time`）はタイムゾーンを持たず、JST での値を表す。日時（`datetime`）はタイムゾーン付き（`Asia/Tokyo`）で持つ。
- 月は `YYYY-MM` 形式の文字列（例: `2026-09`）で持つ。API のパスと通知の記録（`notification_log`）の対象期間の書き方に揃えるためである。
- 不変条件は、構造を生成するモジュールが満たす。本モジュールは生成時に検査しない（判定の規則を持たないため）。
- 各構造の単位（1件が何を表すか）は変えない。


### Status

- 定義
```python
class Status(StrEnum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                         |
| ------------ | --- | ---- | -------------------------------------------- |
| `CONFIRMED`  | str | 〇   | 確定。カテゴリが決まっている記録             |
| `PENDING`    | str | 〇   | 確認待ち。カテゴリが未設定で、アプリで選ぶ記録 |

<!-- 必須は 〇、値が無いことがあるものは - -->

- 不変条件
  - 1つの値が、記録1件の状態を表す。
  - 値の文字列は `transactions` テーブルの `status` 列の値（`confirmed` / `pending`）と一致する。
  - 状態をどう決めるかは持たない。決めるのは分類を受け持つモジュール（`classifier`）である（→ [design.md 8. 分類の方針](../design.md#8-分類の方針)）。


### Source

- 定義
```python
class Source(StrEnum):
    GMAIL = "gmail"
    DISCORD = "discord"
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                     |
| ------------ | --- | ---- | ---------------------------------------- |
| `GMAIL`      | str | 〇   | Gmail の利用通知メールからの自動取り込み |
| `DISCORD`    | str | 〇   | Discord の bot に送った現金の記録        |

- 不変条件
  - 1つの値が、記録1件の入口を表す。
  - 値の文字列は `transactions` テーブルの `source` 列の値と一致し、重複排除キー（`source_ref`）の先頭の部分（`gmail:` / `discord:` のコロンより前）とも一致する。
  - スマホアプリは記録を追加しないため、アプリを表す値は持たない（→ [design.md 4.3](../design.md#4-処理の流れ)）。


### RecordOutcome

- 定義
```python
class RecordOutcome(StrEnum):
    RECORDED = "recorded"
    DUPLICATE = "duplicate"
    DELETED = "deleted"
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                                                     |
| ------------ | --- | ---- | ------------------------------------------------------------------------ |
| `RECORDED`   | str | 〇   | 新しい記録として保存した                                                 |
| `DUPLICATE`  | str | 〇   | 同じ重複排除キーの記録が既にあるため、保存しなかった                     |
| `DELETED`    | str | 〇   | 同じ重複排除キーの記録が過去に削除されている（`deleted_refs` にある）ため、保存しなかった |

- 不変条件
  - 1つの値が、1件の支払いを記録しようとした1回の結果を表す。
  - 保存しなかった理由は、重複と削除済みの2つに限る。解析できなかった支払いは記録の試みに至らないため、この列挙には含めない。
  - DB には保存しない。記録（`recorder`）から呼び出し元への受け渡しだけに使う。


### PaymentTiming

- 定義
```python
class PaymentTiming(StrEnum):
    IMMEDIATE = "immediate"
    CARD = "card"
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                                         |
| ------------ | --- | ---- | ------------------------------------------------------------ |
| `IMMEDIATE`  | str | 〇   | 即時に支払う。現金や、残高・口座から即時に引き落とす決済     |
| `CARD`       | str | 〇   | 締め日で締めて、後日まとめて引き落とす。クレジットカードなど |

- 不変条件
  - 1つの値が、支払い手段1つの支払い方を表す。
  - 値の文字列は設定ファイル（`config.toml`）の `timing` の値と一致する（→ [design.md 7.1 支払日の決め方](../design.md#71-支払日の決め方)）。


### PaymentRule

- 定義
```python
@dataclass(frozen=True)
class PaymentRule:
    payment_method: str
    timing: PaymentTiming
    closing_day: int | None = None
    withdrawal_day: int | None = None
    withdrawal_month_offset: int | None = None
```

- フィールド一覧

| フィールド名              | 型             | 必須 | 内容                                                                 |
| ------------------------- | -------------- | ---- | -------------------------------------------------------------------- |
| `payment_method`          | str            | 〇   | 支払い手段（`楽天カード`、`現金` など）                              |
| `timing`                  | PaymentTiming  | 〇   | 支払い方                                                             |
| `closing_day`             | int \| None    | -    | 締め日（1〜31。31 は月末を表す）。即時なら `None`                    |
| `withdrawal_day`          | int \| None    | -    | 引き落とし日（1〜31。31 は月末を表す）。即時なら `None`              |
| `withdrawal_month_offset` | int \| None    | -    | 締めた月の何か月後に引き落とすか（1以上）。即時なら `None`           |

- 不変条件
  - 1件が、支払い手段1つの締め日のルールを表す。同じ支払い手段のルールは2つ存在しない。
  - 支払い手段（`payment_method`）は空文字にならず、`ParsedPayment` / `Transaction` の支払い手段と同じ文字列で照合する。
  - 支払い方（`timing`）が即時（`IMMEDIATE`）であることと、締め日・引き落とし日・何か月後かの3つがすべて `None` であることは同値である。締めてから引き落とす（`CARD`）ときは、3つとも `None` でない。
  - DB には保存しない。設定の読み込み（`config`）が設定ファイルから作る。
  - 本構造は支払日の計算の規則を持たない。計算は `paid_date` の設計書と [design.md 7.1 支払日の決め方](../design.md#71-支払日の決め方) で定める。


### MailMessage

- 定義
```python
@dataclass(frozen=True)
class MailMessage:
    message_id: str
    sender: str
    subject: str
    body: str
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                                     |
| ------------ | --- | ---- | -------------------------------------------------------- |
| `message_id` | str | 〇   | Gmail のメッセージ ID                                    |
| `sender`     | str | 〇   | 送り主。From ヘッダーの値を加工せずに入れる              |
| `subject`    | str | 〇   | 件名。件名が無いメールでは空文字                         |
| `body`       | str | 〇   | 本文のテキスト。テキストの本文が取り出せない場合は空文字 |

- 不変条件
  - 1件が Gmail のメール1通を表す。
  - メールの ID（`message_id`）は空文字にならない。
  - 送り主（`sender`）からメールアドレスを取り出して解析器を選ぶのはメールの解析（`mail_parser`）であり、本構造は取り出し済みの値を持たない。
  - 受信日時を持たない。支払いの利用日・時刻を受信時刻で埋めない（→ [design.md 7. データフロー](../design.md#7-データフロー)）ため、解析に渡さない。


### ParsedPayment

- 定義
```python
@dataclass(frozen=True)
class ParsedPayment:
    occurred_date: date
    occurred_time: time | None
    amount: int
    merchant: str
    payment_method: str
    source: Source
    source_ref: str
```

- フィールド一覧

| フィールド名     | 型            | 必須 | 内容                                                                       |
| ---------------- | ------------- | ---- | -------------------------------------------------------------------------- |
| `occurred_date`  | date          | 〇   | 利用日。使った日（JST）                                                    |
| `occurred_time`  | time \| None  | -    | 使った時刻（JST、時と分）。分からなければ `None`                           |
| `amount`         | int           | 〇   | 金額（円）                                                                 |
| `merchant`       | str           | 〇   | 店名、または bot に送ったメモ。生の文字列のまま持つ。無ければ空文字        |
| `payment_method` | str           | 〇   | 支払い手段（`楽天カード`、`現金` など）                                    |
| `source`         | Source        | 〇   | 記録の入口                                                                 |
| `source_ref`     | str           | 〇   | 重複排除キー                                                               |

- 不変条件
  - 1件が、まだ保存していない支払い1件を表す。メール1通から複数件が作られることがある。
  - 自動取り込みではメールの解析（`mail_parser`）が生成する。現金では Discord の bot（`discord_bot`）が、メッセージを分解した結果（`CashEntry`）とメッセージの送信時刻から生成する。記録（`recorder`）はどちらの入口の支払いもこの構造で受け取る。
  - 金額（`amount`）は1以上の整数である。
  - 時刻（`occurred_time`）は秒とマイクロ秒を0とし、タイムゾーンを持たない。
  - 店名（`merchant`）は正規化しない。照合キーは分類（`classifier`）で別に作る（→ `Classification`）。
  - 支払い手段（`payment_method`）は空文字にならない。
  - 重複排除キー（`source_ref`）は、Gmail なら `gmail:{message_id}:{メール内の連番}`、Discord なら `discord:{message_id}` の形であり、先頭の部分は入口（`source`）の値と一致する。連番の振り方は `mail_parser` の設計書で定める。
  - 同じ支払いからは常に同じ重複排除キーが作られる。
  - 支払日は持たない。支払日は記録（`recorder`）が、支払い手段のルール（`PaymentRule`）を使って計算する。解析するモジュールに締め日の知識を持たせないためである。


### CashEntry

- 定義
```python
@dataclass(frozen=True)
class CashEntry:
    memo: str
    amount: int
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                                       |
| ------------ | --- | ---- | ---------------------------------------------------------- |
| `memo`       | str | 〇   | メモ。金額だけが送られた場合は空文字                       |
| `amount`     | int | 〇   | 金額（円）                                                 |

- 不変条件
  - 1件が、Discord のメッセージ1件を分解した結果を表す。1件のメッセージから複数件は作らない。
  - 金額（`amount`）は1以上の整数である。解析できないメッセージ（金額が無い、0円以下など）では本構造を作らない。
  - メモ（`memo`）は正規化しない。メッセージのどこまでをメモとするか、前後の空白をどう扱うかは `cash_parser` の設計書で定める。
  - 利用日・時刻・支払い手段・重複排除キーは持たない。これらは Discord の bot（`discord_bot`）がメッセージから決め、記録する前の支払い（`ParsedPayment`）に入れる。


### Classification

- 定義
```python
@dataclass(frozen=True)
class Classification:
    merchant_key: str
    category_id: int | None
    status: Status
```

- フィールド一覧

| フィールド名   | 型           | 必須 | 内容                                               |
| -------------- | ------------ | ---- | -------------------------------------------------- |
| `merchant_key` | str          | 〇   | 店名・メモを正規化した照合キー。店名・メモが空なら空文字 |
| `category_id`  | int \| None  | -    | 決まったカテゴリの ID。未設定なら `None`           |
| `status`       | Status       | 〇   | 記録の状態                                         |

- 不変条件
  - 1件が、支払い1件に対する分類の結果を表す。
  - 照合キー（`merchant_key`）は、店名・メモを `normalize` に通した結果と一致する。
  - 状態が確定（`CONFIRMED`）であることと、カテゴリ（`category_id`）が `None` でないことは同値である。
  - 照合キーが空文字のときは、カテゴリが `None`、状態が確認待ち（`PENDING`）である。
  - 本構造はカテゴリの決め方を持たない。決め方は `classifier` の設計書と [design.md 8. 分類の方針](../design.md#8-分類の方針) で定める。


### MerchantRule

- 定義
```python
@dataclass(frozen=True)
class MerchantRule:
    merchant_key: str
    category_id: int
```

- フィールド一覧

| フィールド名   | 型  | 必須 | 内容                 |
| -------------- | --- | ---- | -------------------- |
| `merchant_key` | str | 〇   | 照合キー             |
| `category_id`  | int | 〇   | 分類先のカテゴリの ID |

- 不変条件
  - 1件が、照合キー1つに対する分類ルールを表す。同じ照合キーのルールは2つ存在しない（`merchant_rules` の主キー）。
  - 照合キー（`merchant_key`）は空文字にならない。店名・メモが空の記録からはルールを作らないためである（→ [design.md 8. 分類の方針](../design.md#8-分類の方針)）。
  - カテゴリ（`category_id`）は、存在するカテゴリの ID である。


### Category

- 定義
```python
@dataclass(frozen=True)
class Category:
    id: int
    name: str
    emoji: str
    sort_order: int
```

- フィールド一覧

| フィールド名 | 型  | 必須 | 内容                                       |
| ------------ | --- | ---- | ------------------------------------------ |
| `id`         | int | 〇   | カテゴリの ID                              |
| `name`       | str | 〇   | 名前（`食費` など）                        |
| `emoji`      | str | 〇   | bot の返事とリアクションに使う絵文字       |
| `sort_order` | int | 〇   | 表示順。小さいものを先に表示する           |

- 不変条件
  - 1件がカテゴリ1つを表す。カテゴリは1階層で、親子を持たない。
  - 名前（`name`）と絵文字（`emoji`）は空文字にならず、それぞれカテゴリ全体で一意である。
  - 「未分類」はカテゴリとして存在しない。カテゴリが未設定であることは、カテゴリの ID が `None` であることで表す。
  - カテゴリは削除されないため、記録やルールが参照する ID は常に存在する。


### CategoryUpdate

- 定義
```python
@dataclass(frozen=True)
class CategoryUpdate:
    name: str | None = None
    emoji: str | None = None
    sort_order: int | None = None
```

- フィールド一覧

| フィールド名 | 型           | 必須 | 内容                                     |
| ------------ | ------------ | ---- | ---------------------------------------- |
| `name`       | str \| None  | -    | 新しい名前。変えないなら `None`          |
| `emoji`      | str \| None  | -    | 新しい絵文字。変えないなら `None`        |
| `sort_order` | int \| None  | -    | 新しい表示順。変えないなら `None`        |

- 不変条件
  - 1件が、カテゴリ1つに対する変更の指示を表す。対象のカテゴリの ID は本構造に含めず、呼び出す側が別に渡す。
  - `None` は「変えない」を表す。すべてが `None` の指示は、何も変えない指示である。
  - 名前・絵文字に空文字を入れない。
  - 変更後に名前・絵文字の一意性が保たれるかの判定は持たない（`repository` の一意制約と、呼び出す側で扱う）。


### Transaction

- 定義
```python
@dataclass(frozen=True)
class Transaction:
    id: int
    occurred_date: date
    occurred_time: time | None
    paid_date: date
    amount: int
    merchant: str
    merchant_key: str
    category_id: int | None
    status: Status
    payment_method: str
    source: Source
    source_ref: str
    created_at: datetime
    updated_at: datetime
```

- フィールド一覧

| フィールド名     | 型            | 必須 | 内容                                                   |
| ---------------- | ------------- | ---- | ------------------------------------------------------ |
| `id`             | int           | 〇   | 記録の ID                                              |
| `occurred_date`  | date          | 〇   | 利用日。使った日（JST）                                |
| `occurred_time`  | time \| None  | -    | 使った時刻（JST、時と分）。分からなければ `None`       |
| `paid_date`      | date          | 〇   | 支払日。口座などからお金が出ていく日（JST）            |
| `amount`         | int           | 〇   | 金額（円）                                             |
| `merchant`       | str           | 〇   | 店名・メモ（生の文字列）。無ければ空文字               |
| `merchant_key`   | str           | 〇   | 正規化した店名・メモ。無ければ空文字                   |
| `category_id`    | int \| None   | -    | カテゴリの ID。未設定なら `None`                       |
| `status`         | Status        | 〇   | 記録の状態                                             |
| `payment_method` | str           | 〇   | 支払い手段                                             |
| `source`         | Source        | 〇   | 記録の入口                                             |
| `source_ref`     | str           | 〇   | 重複排除キー                                           |
| `created_at`     | datetime      | 〇   | 作成日時（JST、タイムゾーン付き）                      |
| `updated_at`     | datetime      | 〇   | 更新日時（JST、タイムゾーン付き）                      |

- 不変条件
  - 1件が、保存済みの記録1件（`transactions` テーブルの1行）を表す。
  - 金額（`amount`）は1以上の整数である。
  - 時刻（`occurred_time`）は秒とマイクロ秒を0とし、タイムゾーンを持たない。
  - 支払日（`paid_date`）は利用日（`occurred_date`）より前にならない。記録したときはルールから計算した値であり、アプリで直したあとは直した値である。
  - 照合キー（`merchant_key`）は、店名・メモ（`merchant`）を `normalize` に通した結果と一致する。
  - 状態が確定（`CONFIRMED`）であることと、カテゴリ（`category_id`）が `None` でないことは同値である。
  - 重複排除キー（`source_ref`）は記録全体で一意であり、先頭の部分は入口（`source`）の値と一致する。
  - 更新日時（`updated_at`）は作成日時（`created_at`）より前にならない。
  - 削除済みの記録は本構造で表さない（削除は物理削除で、重複排除キーだけが `deleted_refs` に残る）。


### TransactionUpdate

- 定義
```python
@dataclass(frozen=True)
class TransactionUpdate:
    occurred_date: date | None = None
    paid_date: date | None = None
    amount: int | None = None
    merchant: str | None = None
    category_id: int | None = None
```

- フィールド一覧

| フィールド名    | 型            | 必須 | 内容                                                 |
| --------------- | ------------- | ---- | ---------------------------------------------------- |
| `occurred_date` | date \| None  | -    | 新しい利用日。変えないなら `None`                    |
| `paid_date`     | date \| None  | -    | 新しい支払日。変えないなら `None`                    |
| `amount`        | int \| None   | -    | 新しい金額（円）。変えないなら `None`                |
| `merchant`      | str \| None   | -    | 新しい店名・メモ（生の文字列）。変えないなら `None`  |
| `category_id`   | int \| None   | -    | 選んだカテゴリの ID。変えないなら `None`             |

- 不変条件
  - 1件が、記録1件に対する修正の指示を表す。対象の記録の ID は本構造に含めず、呼び出す側が別に渡す。
  - `None` は「変えない」を表す。すべてが `None` の指示は、何も変えない指示である。
  - 金額（`amount`）を入れる場合は1以上の整数である。
  - カテゴリを未設定に戻す指示は表せない。確定の記録を確認待ちに戻す経路が無いためである（→ [design.md 8. 分類の方針](../design.md#8-分類の方針)）。
  - 修正できる項目は、アプリで修正できる項目（金額・利用日・支払日・店名・カテゴリ）に限る（→ [design.md 4.3](../design.md#4-処理の流れ)）。時刻・支払い手段・入口・重複排除キーは修正できない。
  - 店名を変えたときの照合キーの作り直し、利用日だけを変えたときの支払日の計算し直し、カテゴリを選んだときの確定とルールの学習は持たない。これらは修正を受け持つサービス層が行う（→ [design.md 4.3](../design.md#4-処理の流れ)）。


### IncomeInput

- 定義
```python
@dataclass(frozen=True)
class IncomeInput:
    received_date: date
    amount: int
    memo: str
```

- フィールド一覧

| フィールド名    | 型   | 必須 | 内容                                                   |
| --------------- | ---- | ---- | ------------------------------------------------------ |
| `received_date` | date | 〇   | 入金日（JST）                                          |
| `amount`        | int  | 〇   | 金額（円）                                             |
| `memo`          | str  | 〇   | メモ（`給与` など）。生の文字列のまま持つ。無ければ空文字 |

- 不変条件
  - 1件が、アプリから入力された、まだ保存していない収入1件を表す。
  - 金額（`amount`）は1以上の整数である。
  - 収入はアプリからしか入らないため、入口・重複排除キーは持たない（→ [ADR-0005](../adr/0005-income-manual-entry-from-app.md)）。
  - カテゴリは持たない。収入は分類しない。


### Income

- 定義
```python
@dataclass(frozen=True)
class Income:
    id: int
    received_date: date
    amount: int
    memo: str
    created_at: datetime
    updated_at: datetime
```

- フィールド一覧

| フィールド名    | 型       | 必須 | 内容                                   |
| --------------- | -------- | ---- | -------------------------------------- |
| `id`            | int      | 〇   | 収入の ID                              |
| `received_date` | date     | 〇   | 入金日（JST）                          |
| `amount`        | int      | 〇   | 金額（円）                             |
| `memo`          | str      | 〇   | メモ（生の文字列）。無ければ空文字     |
| `created_at`    | datetime | 〇   | 作成日時（JST、タイムゾーン付き）      |
| `updated_at`    | datetime | 〇   | 更新日時（JST、タイムゾーン付き）      |

- 不変条件
  - 1件が、保存済みの収入1件（`incomes` テーブルの1行）を表す。支出の記録（`Transaction`）とは別の構造であり、支出の集計・予算の判定には含めない。
  - 金額（`amount`）は1以上の整数である。
  - 更新日時（`updated_at`）は作成日時（`created_at`）より前にならない。
  - 削除済みの収入は本構造で表さない（削除は物理削除である）。


### IncomeUpdate

- 定義
```python
@dataclass(frozen=True)
class IncomeUpdate:
    received_date: date | None = None
    amount: int | None = None
    memo: str | None = None
```

- フィールド一覧

| フィールド名    | 型            | 必須 | 内容                                        |
| --------------- | ------------- | ---- | ------------------------------------------- |
| `received_date` | date \| None  | -    | 新しい入金日。変えないなら `None`           |
| `amount`        | int \| None   | -    | 新しい金額（円）。変えないなら `None`       |
| `memo`          | str \| None   | -    | 新しいメモ（生の文字列）。変えないなら `None` |

- 不変条件
  - 1件が、収入1件に対する修正の指示を表す。対象の収入の ID は本構造に含めず、呼び出す側が別に渡す。
  - `None` は「変えない」を表す。すべてが `None` の指示は、何も変えない指示である。
  - 金額（`amount`）を入れる場合は1以上の整数である。
  - メモを空にする指示は、空文字で表す。


### RecordResult

- 定義
```python
@dataclass(frozen=True)
class RecordResult:
    outcome: RecordOutcome
    transaction: Transaction | None
    category: Category | None
    budget: BudgetStatus | None
```

- フィールド一覧

| フィールド名  | 型                     | 必須 | 内容                                                                     |
| ------------- | ---------------------- | ---- | ------------------------------------------------------------------------ |
| `outcome`     | RecordOutcome          | 〇   | 記録の結果                                                               |
| `transaction` | Transaction \| None    | -    | 保存した記録。保存しなかったときは `None`                                |
| `category`    | Category \| None       | -    | 保存した記録のカテゴリ。未設定のとき、または保存しなかったときは `None`  |
| `budget`      | BudgetStatus \| None   | -    | 保存した記録の支払日が属する月の、保存後の予算の状況。保存しなかったときは `None` |

- 不変条件
  - 1件が、支払い1件を記録しようとした1回の結果を表す。
  - 結果（`outcome`）が保存した（`RECORDED`）であることと、保存した記録（`transaction`）と予算の状況（`budget`）がともに `None` でないことは同値である。
  - 保存しなかった（`DUPLICATE` / `DELETED`）ときは、保存した記録・カテゴリ・予算の状況がすべて `None` である。
  - カテゴリ（`category`）は、保存した記録のカテゴリの ID が `None` でないときに限り入り、その ID（`category.id`）は記録のカテゴリの ID と一致する。bot の返事にカテゴリの名前と絵文字を出すために、ID だけでなくカテゴリそのものを持つ。
  - 予算の状況の月（`budget.month`）は、保存した記録の支払日（`paid_date`）が属する月と一致する（→ [ADR-0004](../adr/0004-monthly-totals-by-paid-date.md)）。


### BudgetStatus

- 定義
```python
@dataclass(frozen=True)
class BudgetStatus:
    month: str
    budget: int
    spent: int
    remaining: int
    newly_crossed: tuple[int, ...]
```

- フィールド一覧

| フィールド名    | 型               | 必須 | 内容                                                       |
| --------------- | ---------------- | ---- | ---------------------------------------------------------- |
| `month`         | str              | 〇   | 対象の月（`YYYY-MM`）                                      |
| `budget`        | int              | 〇   | 月の予算（円）                                             |
| `spent`         | int              | 〇   | その月の支出合計（円）。支払日がその月に属する記録の金額の和 |
| `remaining`     | int              | 〇   | 残りの金額（円）。予算を超えていれば負の数                 |
| `newly_crossed` | tuple[int, ...]  | 〇   | 今回新たに超えた閾値（予算に対する百分率。例: `80`）。無ければ空の列 |

- 不変条件
  - 1件が、1つの月の予算の状況を表す。
  - 残り（`remaining`）は、予算（`budget`）から支出合計（`spent`）を引いた値と一致する。
  - 支出合計は0以上である。
  - 新たに超えた閾値（`newly_crossed`）は、小さい順に並び、同じ値を2度含まない。
  - 閾値の値（80 / 100）と、「新たに」をどう判定するかは持たない。どちらも `budget` の設計書で定める。
  - 支払日が前月以前の記録では閾値を判定しないため、そのときの新たに超えた閾値は空の列である。支払日が来月以降の記録では判定する（→ [design.md 4.4 通知](../design.md#44-通知)）。


### CategoryTotal

- 定義
```python
@dataclass(frozen=True)
class CategoryTotal:
    category: Category | None
    amount: int
```

- フィールド一覧

| フィールド名 | 型                | 必須 | 内容                                         |
| ------------ | ----------------- | ---- | -------------------------------------------- |
| `category`   | Category \| None  | -    | カテゴリ。カテゴリが未設定の記録の合計なら `None` |
| `amount`     | int               | 〇   | 期間内の支出合計（円）                       |

- 不変条件
  - 1件が、ある期間の、カテゴリ1つ分（または未分類分）の支出合計を表す。期間は本構造を持つ集計（`MonthlySummary` / `WeeklySummary`）が決める。
  - 金額（`amount`）は1以上である。期間内に記録の無いカテゴリは含めない。
  - 確認待ちの記録は、カテゴリが `None` の1件にまとめて数える。
  - 列として並べるときは、金額の多い順に並べる。金額が同じなら表示順（`sort_order`）の小さい順とし、未分類はそれらの後に置く。


### MonthlySummary

- 定義
```python
@dataclass(frozen=True)
class MonthlySummary:
    month: str
    income_total: int
    total: int
    balance: int
    budget: int
    remaining: int
    by_category: tuple[CategoryTotal, ...]
```

- フィールド一覧

| フィールド名  | 型                          | 必須 | 内容                                       |
| ------------- | --------------------------- | ---- | ------------------------------------------ |
| `month`       | str                         | 〇   | 対象の月（`YYYY-MM`）                      |
| `income_total`| int                         | 〇   | 月の収入合計（円）                         |
| `total`       | int                         | 〇   | 月の支出合計（円）                         |
| `balance`     | int                         | 〇   | 収支（円）。収入合計から支出合計を引いた値。負の数がありうる |
| `budget`      | int                         | 〇   | 月の予算（円）                             |
| `remaining`   | int                         | 〇   | 残りの金額（円）。予算を超えていれば負の数 |
| `by_category` | tuple[CategoryTotal, ...]   | 〇   | カテゴリ別の内訳。記録が無ければ空の列     |

- 不変条件
  - 1件が、1つの月（支払日が JST でその月に属する記録すべて）の集計を表す。利用日では数えない（→ [ADR-0004](../adr/0004-monthly-totals-by-paid-date.md)）。
  - 収入合計（`income_total`）は、入金日が JST でその月に属する収入（`Income`）の金額の和である。収入が無い月は0である。
  - 支出合計（`total`）は、カテゴリ別の内訳の金額の和と一致する。記録が無い月の支出合計は0である。
  - 収支（`balance`）は、収入合計から支出合計を引いた値と一致する。
  - 残り（`remaining`）は、予算（`budget`）から支出合計を引いた値と一致する。収入は予算の残りに影響しない。
  - カテゴリ別の内訳の並びは `CategoryTotal` の並べ方に従う。
  - 前月との差は持たない。月のまとめでは、文面の組み立て（`summary`）で2か月分の集計から差を計算する。
  - API の月の集計（`/months/{YYYY-MM}/summary`）と、月のまとめの通知の両方で使う。


### WeeklySummary

- 定義
```python
@dataclass(frozen=True)
class WeeklySummary:
    week_start: date
    week_end: date
    total: int
    by_category: tuple[CategoryTotal, ...]
    month_remaining: int
    pending_count: int
```

- フィールド一覧

| フィールド名      | 型                         | 必須 | 内容                                                     |
| ----------------- | -------------------------- | ---- | -------------------------------------------------------- |
| `week_start`      | date                       | 〇   | 週の初日（月曜）                                         |
| `week_end`        | date                       | 〇   | 週の最終日（日曜）                                       |
| `total`           | int                        | 〇   | 週の支出合計（円）。利用日がその週に属する記録の金額の和 |
| `by_category`     | tuple[CategoryTotal, ...]  | 〇   | 週のカテゴリ別の内訳。記録が無ければ空の列               |
| `month_remaining` | int                        | 〇   | 週の最終日が属する月の、予算の残り（円。支払日で数える）。負の数がありうる |
| `pending_count`   | int                        | 〇   | 集計した時点で確認待ちになっている記録の件数             |

- 不変条件
  - 1件が、1つの週（月曜〜日曜、JST）の集計を表す。週の記録は利用日で数える。支払日で数えると、引き落とし日のある週に支出がまとめて出てしまうためである（→ [ADR-0004](../adr/0004-monthly-totals-by-paid-date.md)）。
  - 予算の残り（`month_remaining`）だけは、月の集計と同じく支払日で数える。
  - 週の初日（`week_start`）は月曜、最終日（`week_end`）はその6日後の日曜である。週が月をまたいでも分けない。
  - 支出合計（`total`）は、カテゴリ別の内訳の金額の和と一致する。
  - カテゴリ別の内訳は上位3つに絞らず、すべてを持つ。絞り込みは文面を組み立てる `summary` が行う。並びは `CategoryTotal` の並べ方に従う。
  - 確認待ちの件数（`pending_count`）は、週の期間に限らず、集計した時点で確認待ちのすべての記録を数える。0以上である。


### Settings

- 定義
```python
@dataclass(frozen=True)
class Settings:
    monthly_budget: int
    record_channel_id: int
    owner_user_id: int
    gmail_label: str
```

- フィールド一覧

| フィールド名        | 型  | 必須 | 内容                                   |
| ------------------- | --- | ---- | -------------------------------------- |
| `monthly_budget`    | int | 〇   | 月の予算（円）                         |
| `record_channel_id` | int | 〇   | 記録用チャンネルの Discord の ID       |
| `owner_user_id`     | int | 〇   | 自分の Discord ユーザーの ID           |
| `gmail_label`       | str | 〇   | 取り込み対象の Gmail のラベル名（`家計簿` など） |

- 不変条件
  - 1件が、サーバーの設定一式（`settings` テーブルの内容全体）を表す。設定は1組だけ存在する。
  - 月の予算（`monthly_budget`）は1以上の整数である。予算は全体で1つだけであり、カテゴリごとの予算は持たない。
  - Gmail のラベル名（`gmail_label`）は空文字にならない。
  - 支払い手段の締め日のルールは持たない。ルールは設定ファイルに書き、`PaymentRule` として読む（→ [design.md 7.1 支払日の決め方](../design.md#71-支払日の決め方)）。
  - 秘密情報（Discord のトークン、API のトークン、Google のクライアント情報と認証情報）は持たない。これらは設定の読み込み（`config`）で環境変数とサーバー上のファイルから読む（→ [design.md 11. 非機能](../design.md#11-非機能)）。


### ImportFailure

- 定義
```python
@dataclass(frozen=True)
class ImportFailure:
    message_id: str
    sender: str
    subject: str
    reason: str
    failed_at: datetime
```

- フィールド一覧

| フィールド名 | 型       | 必須 | 内容                                         |
| ------------ | -------- | ---- | -------------------------------------------- |
| `message_id` | str      | 〇   | Gmail のメッセージ ID                        |
| `sender`     | str      | 〇   | 送り主（`MailMessage` の送り主と同じ値）     |
| `subject`    | str      | 〇   | 件名（`MailMessage` の件名と同じ値）         |
| `reason`     | str      | 〇   | 解析できなかった理由                         |
| `failed_at`  | datetime | 〇   | 解析に失敗した日時（JST、タイムゾーン付き）  |

- 不変条件
  - 1件が、取り込めなかったメール1通を表す。同じメッセージ ID の失敗は2件存在しない。
  - メールの ID・送り主・件名は、解析に渡したメール（`MailMessage`）の値をそのまま写す。
  - 理由（`reason`）は空文字にならない。理由の文言は `mail_parser` の設計書で定める。
  - 本文は持たない。アプリと通知で見せるのは送り主と件名だけである（→ [design.md 4.4 通知](../design.md#44-通知)）。


### NotificationLog

- 定義
```python
@dataclass(frozen=True)
class NotificationLog:
    kind: str
    period: str
    sent_at: datetime
```

- フィールド一覧

| フィールド名 | 型       | 必須 | 内容                                                   |
| ------------ | -------- | ---- | ------------------------------------------------------ |
| `kind`       | str      | 〇   | 通知の種類（例: `budget_80`）                          |
| `period`     | str      | 〇   | 通知の対象期間（例: `2026-09`）                        |
| `sent_at`    | datetime | 〇   | 送った日時（JST、タイムゾーン付き）                    |

- 不変条件
  - 1件が、送った通知1回を表す。種類（`kind`）と対象期間（`period`）の組は一意である。
  - 予算の到達の通知では、種類は `budget_{閾値}`（例: `budget_80` / `budget_100`）、対象期間は対象の月（`YYYY-MM`）である。閾値は `BudgetStatus` の新たに超えた閾値の値と同じ数である。
  - 種類の値として定めるのは予算の到達だけである。週・月のまとめと取り込めないメールの通知を記録するかは、基本設計で決まっていない。
