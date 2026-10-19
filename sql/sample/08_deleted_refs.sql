-- 削除した記録の重複排除キー（04_transactions.sql には無いキー）
INSERT INTO deleted_refs (source_ref) VALUES
    ('gmail:sample1001a:0');
