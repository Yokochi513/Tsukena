-- Tsukena の DB のテーブル定義（→ docs/design.md 9. データモデル）
-- 日付は YYYY-MM-DD、時刻は HH:MM、日時は ISO 8601 のタイムゾーン付き（+09:00）の文字列で持つ。すべて JST。

-- カテゴリ
CREATE TABLE categories (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL UNIQUE CHECK (name <> ''),   -- 名前（一意）
    emoji      TEXT    NOT NULL UNIQUE CHECK (emoji <> ''),  -- bot の返事とリアクションに使う絵文字（一意）
    sort_order INTEGER NOT NULL                              -- 表示順
);

-- 支出の記録
CREATE TABLE transactions (
    id             INTEGER PRIMARY KEY,
    occurred_date  TEXT    NOT NULL CHECK (occurred_date IS date(occurred_date)),       -- 利用日 YYYY-MM-DD（JST）
    occurred_time  TEXT             CHECK (occurred_time IS NULL
                                           OR occurred_time IS strftime('%H:%M', occurred_time)), -- 利用時刻 HH:MM。分からなければ NULL
    paid_date      TEXT    NOT NULL CHECK (paid_date IS date(paid_date)),               -- 支払日 YYYY-MM-DD（JST）
    amount         INTEGER NOT NULL CHECK (amount >= 1),                               -- 円、正の整数
    merchant       TEXT    NOT NULL DEFAULT '',                                        -- 店名・メモ（生の文字列）。無ければ空文字
    merchant_key   TEXT    NOT NULL DEFAULT '',                                        -- 正規化した店名・メモ。無ければ空文字
    memo           TEXT    NOT NULL DEFAULT '',                                        -- 買った物などの覚え書き（アプリで書く）。無ければ空文字
    category_id    INTEGER          REFERENCES categories (id),                        -- 未設定なら NULL
    status         TEXT    NOT NULL CHECK (status IN ('confirmed', 'pending')),
    payment_method TEXT    NOT NULL CHECK (payment_method <> ''),                      -- 現金、楽天カード など
    source         TEXT    NOT NULL CHECK (source IN ('gmail', 'discord')),
    source_ref     TEXT    NOT NULL UNIQUE,                                            -- 重複排除キー（gmail:{message_id}:{連番} / discord:{message_id}）
    created_at     TEXT    NOT NULL,                                                   -- 作成日時（JST、タイムゾーン付き）
    updated_at     TEXT    NOT NULL,                                                   -- 更新日時
    CHECK (paid_date >= occurred_date),
    CHECK (status <> 'confirmed' OR category_id IS NOT NULL),
    CHECK (source_ref LIKE source || ':%'),
    CHECK (updated_at >= created_at)
);

CREATE INDEX idx_transactions_paid_date     ON transactions (paid_date);
CREATE INDEX idx_transactions_occurred_date ON transactions (occurred_date);
CREATE INDEX idx_transactions_status        ON transactions (status);

-- 収入（→ docs/adr/0005-income-manual-entry-from-app.md）
CREATE TABLE incomes (
    id            INTEGER PRIMARY KEY,
    received_date TEXT    NOT NULL CHECK (received_date IS date(received_date)), -- 入金日 YYYY-MM-DD（JST）
    amount        INTEGER NOT NULL CHECK (amount >= 1),                         -- 円、正の整数
    memo          TEXT    NOT NULL DEFAULT '',                                  -- 無ければ空文字
    created_at    TEXT    NOT NULL,                                             -- 作成日時（JST、タイムゾーン付き）
    updated_at    TEXT    NOT NULL,                                             -- 更新日時
    CHECK (updated_at >= created_at)
);

CREATE INDEX idx_incomes_received_date ON incomes (received_date);

-- 分類ルール
CREATE TABLE merchant_rules (
    merchant_key TEXT    PRIMARY KEY CHECK (merchant_key <> ''),     -- 照合キー（正規化した店名・メモ）
    category_id  INTEGER NOT NULL REFERENCES categories (id)        -- 分類先のカテゴリ
);

-- サーバーの設定。1行だけ持つ（id は常に 1）
-- Discord の ID は持たない。記録と通知は bot の持ち主との DM で行う（→ docs/adr/0008-record-and-notify-via-owner-dm.md）
CREATE TABLE settings (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    monthly_budget INTEGER NOT NULL CHECK (monthly_budget >= 1),  -- 月の予算（円）
    gmail_label    TEXT    NOT NULL CHECK (gmail_label <> ''),    -- 取り込み対象の Gmail のラベル名
    full_import_done INTEGER NOT NULL DEFAULT 0 CHECK (full_import_done IN (0, 1))  -- 全期間の取り込みを済ませたか。済むまでは期間を区切らずに問い合わせる
);

-- 送った通知。同じ種類・同じ対象期間の通知を2度送らないために使う
CREATE TABLE notification_log (
    kind    TEXT NOT NULL CHECK (kind <> ''),    -- 通知の種類（budget_80 / budget_100 / weekly / monthly など）
    period  TEXT NOT NULL CHECK (period <> ''),  -- 対象期間（2026-09 など）
    sent_at TEXT NOT NULL,                       -- 送った日時（JST、タイムゾーン付き）
    PRIMARY KEY (kind, period)
);

-- 取り込めなかったメール
CREATE TABLE import_failures (
    message_id TEXT PRIMARY KEY CHECK (message_id <> ''),  -- Gmail のメッセージ ID
    sender     TEXT NOT NULL,                              -- 送り主（From ヘッダーの値）
    subject    TEXT NOT NULL,                              -- 件名。無ければ空文字
    reason     TEXT NOT NULL,                              -- 解析できなかった理由
    failed_at  TEXT NOT NULL                               -- 解析に失敗した日時（JST、タイムゾーン付き）
);

-- 削除した記録の重複排除キー。消した Gmail 由来の記録が再び取り込まれないようにする
CREATE TABLE deleted_refs (
    source_ref TEXT PRIMARY KEY CHECK (source_ref <> '')
);
