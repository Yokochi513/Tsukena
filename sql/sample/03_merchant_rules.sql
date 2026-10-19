-- 分類ルール（01_categories.sql のカテゴリを参照する）
-- 照合キーは tsukena/normalize.py で正規化した値を入れている
INSERT INTO merchant_rules (merchant_key, category_id) VALUES
    ('スターバックス',         1),
    ('セブンイレブン',         1),
    ('ランチ',                 1),
    ('ユニクロ渋谷店',         6),
    ('jr東日本モバイルsuica',  3),
    ('netflix',                8),
    ('tohoシネマズ',           4),
    ('居酒屋',                 5),
    ('amazon.co.jp',           2);
