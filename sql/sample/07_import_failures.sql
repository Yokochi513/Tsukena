-- 取り込めなかったメール
INSERT INTO import_failures (message_id, sender, subject, reason, failed_at) VALUES
    ('sample1012a', '楽天カード <info@mail.rakuten-card.co.jp>', '【楽天カード】カード利用のお知らせ', '金額が見つかりません', '2026-10-12T08:15:00+09:00');
