# ADR-0008: 記録と通知は、bot の持ち主との DM だけで行う

- 状態: 採用
- 日付: 2026-10-19

## 背景

これまでの設計では、Discord の記録用チャンネルと自分の Discord ユーザーを設定（`settings` の `record_channel_id` / `owner_user_id`）に持ち、そのチャンネルで自分が送ったメッセージだけを記録していた（→ [design.md 4.2](../design.md#42-discord-bot現金)）。
通知（予算の到達・週と月のまとめ・取り込めないメール）も、同じチャンネルに送っていた。

この2つの ID は、Discord の開発者モードで調べて、手で設定に書く必要がある。
自分のユーザーの ID は、bot の持ち主として Discord から取れる。
一方、記録用チャンネルの ID は取れない。bot は入っているサーバーのチャンネルがすべて見えるが、どれが記録用かは Discord には分からない。

## 選択肢

1. 記録用チャンネルと自分のユーザーの ID を設定に持つ（これまでのまま）
2. 記録用チャンネルを、そのチャンネルで送る登録用のコマンドで保存する。自分のユーザーは bot の持ち主から取る
3. チャンネルを使わず、bot の持ち主との DM だけで記録と通知を行う。持ち主は Discord から取る

## 決定

3 を採用する。

- **記録するのは、bot の持ち主が bot との DM で送ったメッセージだけ**とする。サーバーのチャンネルで送ったメッセージには、持ち主のものでも反応しない。
- リアクションによるカテゴリの変更も、DM の中の bot の返事に持ち主が付けたものだけを受け付ける。
- **通知はすべて持ち主への DM で送る。** 予算の到達（現金の記録で超えたとき）は bot のプロセスが、それ以外の通知は API のプロセスが送る（→ [ADR-0007](./0007-bot-accesses-data-through-api.md)）。
- 持ち主は、Discord のアプリの持ち主（Developer Portal でアプリを作ったアカウント）とする。設定には持たず、起動のたびに Discord から取る。
  - bot のプロセスは、接続した後にアプリの情報（`client.application_info()`）から取る。
  - API のプロセスは、bot のトークンで Discord の HTTP の API（`GET /oauth2/applications/@me`）から取り、DM のチャンネルを開いて（`POST /users/@me/channels`）送る。
- アプリを Developer Portal の Team で作った場合は扱わない。利用者は1人で、アプリは個人のアカウントで作る前提とする。
- 設定（`settings` テーブルと `Settings`）から、記録用チャンネルの ID（`record_channel_id`）と自分のユーザーの ID（`owner_user_id`）を外す。環境変数の `CHANNEL_ID` と `OWNER_USER_ID` も持たない。
- bot が受け取るイベントは、DM のメッセージ（`dm_messages`）と DM のリアクション（`dm_reactions`）とする。DM の本文は特権インテントの Message Content Intent が無くても読めるため、**特権インテントは要求しない**。
- DM を確実に開けるよう、自分しかいないサーバーに bot を入れておく。サーバーのチャンネルは記録にも通知にも使わない。

## 結果

- 設定に手で書く Discord の ID が無くなる。初期設定で開発者モードを使って ID を調べる手順が要らない。
- 持ち主以外の人がいるサーバーに bot を入れても、その人のメッセージや、チャンネルでの会話が記録されることはない。
- 特権インテントを使わないので、Developer Portal でインテントを有効にする手順が要らない。
- 記録・返事・通知が1つの DM にまとまる。チャンネルの通知設定に左右されず、DM の通知として届く。
- 起動のたびに Discord から持ち主を取るので、Discord に接続できないと持ち主が分からない。bot のプロセスは接続できなければもともと動けないので、影響は API のプロセスの通知に限られる。持ち主を取れなかったときの通知の扱いは、`notifier` の設計書で決める。
- bot を入れたサーバーが無くても DM を開けるかは、Discord の公式の資料では確かめられていない。そのため、自分しかいないサーバーに bot を入れておく手順は残す。
- 次の文書とファイルを本 ADR に合わせて直す必要がある。
  - [README](../../README.md) の初期設定（記録用のチャンネルを決める手順）
  - [design.md](../design.md) 3章（構成図の「記録用チャンネル」）、4.2（反応する条件）、4.4（通知の送り先）、9章（`settings`）
  - [model_design.md](../module/model_design.md) の `Settings`
  - [discord_bot_design.md](../module/discord_bot_design.md) の反応する操作の方針、`create_bot()` の権限、`_is_from_owner_in_channel()`
  - `sql/create_tables.sql` と `sql/sample/02_settings.sql` の `settings`
  - `tsukena/bot/` の `BotSettings` と、`.env` の `CHANNEL_ID`・`OWNER_USER_ID`
