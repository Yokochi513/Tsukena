# サーバーへの置き方

自宅の Linux サーバー（Raspberry Pi など）で API と bot を常駐させ、Web 版のアプリを Cloudflare Tunnel で外から使えるようにする手順。
構成の理由は [ADR-0009](./adr/0009-web-app-via-cloudflare-tunnel.md) にある。

```
スマホ・PC のブラウザ
   │ HTTPS
   ▼
Cloudflare Access（自分のアカウントでのログイン）
   │
   ▼
Cloudflare Tunnel ──（サーバーからの外向きの接続。ルーターのポートは開けない）
   │
   ▼  サーバーの中
 cloudflared ─▶ 127.0.0.1:8000  tsukena-api（API と Web 版のアプリ）
                     ▲
                     │ 同じ機械の中で呼ぶ
                tsukena-bot ─▶ Discord
```

## 0. 用意するもの

| もの | 内容 |
| --- | --- |
| Linux のサーバー | 64 ビットの Raspberry Pi OS（Bookworm 以降）や Ubuntu など。Python 3.11 以上が入っていること（`python3 --version`） |
| Cloudflare のアカウント | 無料のプランでよい |
| ドメイン | Cloudflare で DNS を管理しているもの。以下では `tsukena.example.com` と書く |
| Discord の bot | Developer Portal で作った bot のトークン。自分しかいないサーバーに招待しておく（README「初期設定」） |
| 手元の PC | Flutter が入っていること。Web 版のアプリをここでビルドする |

## 1. サーバーにコードを置く

以下はサーバーで行う。コードは `/opt/tsukena` に置き、専用のユーザー `tsukena` で動かす（systemd のファイルがこの前提で書かれている）。

```sh
sudo useradd --system --create-home --shell /usr/sbin/nologin tsukena
sudo git clone <このリポジトリの URL> /opt/tsukena
sudo chown -R tsukena:tsukena /opt/tsukena

# uv を tsukena ユーザーに入れ、依存を入れる
sudo -u tsukena sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
cd /opt/tsukena
sudo -u tsukena /home/tsukena/.local/bin/uv sync --frozen
```

## 2. 秘密情報を置く

`deploy/env.example` を `.env` にコピーし、値を埋める。

```sh
sudo -u tsukena cp deploy/env.example .env
sudo -u tsukena chmod 600 .env
sudo -u tsukena nano .env
```

| 変数 | 値 |
| --- | --- |
| `DISCORD_TOKEN` | Discord の bot のトークン |
| `TSUKENA_APP_API_TOKEN` | アプリ用のトークン。下のコマンドで作る |
| `TSUKENA_BOT_API_TOKEN` | bot 用のトークン。下のコマンドで、アプリ用とは別に作る |

```sh
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"
```

開発に使っていたトークンを流用せず、本番用に作り直すほうが安全である。開発中にスクリーンショットなどへ写っている可能性があるためである。

## 3. DB を作る

```sh
sudo -u tsukena .venv/bin/python -m tsukena.init_db
```

テーブルと、カテゴリ・設定の初期値（README「カテゴリ（初期値）」、月の予算 80,000円）だけが入る。
DB が既にあるときは上書きせずに止まる。

開発中の `db/tsukena.db` をそのまま持っていくこともできるが、`sql/sample/` のサンプルの支出・収入が入っているので勧めない。

## 4. Web 版のアプリをビルドして置く

以下は手元の PC で行う。

`app/dart_defines.prod.json` を作る（`.gitignore` に入っているので git には入らない）。

```json
{
  "API_BASE_URL": "https://tsukena.example.com",
  "API_TOKEN": "（手順2の TSUKENA_APP_API_TOKEN の値）"
}
```

```sh
cd app
flutter build web --release --dart-define-from-file=dart_defines.prod.json
```

できた `app/build/web` を、サーバーの `/opt/tsukena/app/build/web` に送る。

```sh
scp -r build/web <サーバー>:/tmp/tsukena-web
# サーバーで
sudo rm -rf /opt/tsukena/app/build/web
sudo mkdir -p /opt/tsukena/app/build
sudo mv /tmp/tsukena-web /opt/tsukena/app/build/web
sudo chown -R tsukena:tsukena /opt/tsukena/app/build
```

API は、起動するときに `app/build/web/index.html` があれば Web 版も配信する（`tsukena/config.toml` の `[web]`）。
トークンを作り直したときは、ビルドもし直す。

## 5. API と bot を常駐させる

```sh
sudo cp /opt/tsukena/deploy/systemd/tsukena-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tsukena-api tsukena-bot tsukena-backup.timer
```

動いているかを確かめる。

```sh
systemctl status tsukena-api tsukena-bot
journalctl -u tsukena-bot -n 20     # 「Discordに接続しました」が出ていればよい
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/categories   # 401 ならよい（トークンなしで断られた）
curl -s http://127.0.0.1:8000/ | head -c 100                                 # Web 版の index.html が返ればよい
```

Discord で bot に `テスト 1` と送り、返事が来れば bot から API までつながっている。確かめた記録は、後でアプリから消す。

## 6. Cloudflare Access を設定する（公開より先に行う）

**この手順を飛ばして手順7に進まないこと。** Access が無いと、URL を知った人がアプリ用のトークンを取り出せる（→ [ADR-0009](./adr/0009-web-app-via-cloudflare-tunnel.md)）。

1. Cloudflare のダッシュボードで **Zero Trust** を開く（初回はチームの名前を決め、無料のプランを選ぶ）。
2. **Access → Applications → Add an application → Self-hosted** を選ぶ。
3. Application domain に `tsukena.example.com` を入れる。
4. Policy を1つ作る。Action は **Allow**、Include は **Emails** に自分のメールアドレスだけを入れる。
5. ログインの方法は、既定の **One-time PIN**（メールに届く番号でログインする）でよい。
6. Session Duration は、ログインし直す手間と安全さの兼ね合いで決める（例: 1 month）。

## 7. Cloudflare Tunnel をつなぐ

サーバーで行う。`cloudflared` の入れ方は Cloudflare の資料（Downloads）に従う。

```sh
cloudflared tunnel login                      # ブラウザでドメインを選ぶ
cloudflared tunnel create tsukena             # トンネルの ID と認証情報のファイルができる
cloudflared tunnel route dns tsukena tsukena.example.com
```

`deploy/cloudflared/config.yml` を `/etc/cloudflared/config.yml` にコピーし、`<TUNNEL_ID>` とホスト名を書き換える。
認証情報のファイル（`~/.cloudflared/<TUNNEL_ID>.json`）も `/etc/cloudflared/` にコピーする。

```sh
sudo cloudflared service install
sudo systemctl status cloudflared
```

## 8. 外から確かめる

スマホのモバイル回線（Wi-Fi を切った状態）で、次を確かめる。

- [ ] `https://tsukena.example.com` を開くと、まず Cloudflare Access のログイン画面が出る
- [ ] ログインすると、アプリの画面が出て、支出・収入・カテゴリの一覧が読める
- [ ] 別のブラウザ（ログインしていない状態）で `https://tsukena.example.com/main.dart.js` を開くと、ログイン画面になり、ファイルが読めない
- [ ] Discord で記録すると、アプリの一覧に出る
- [ ] 翌日、`/opt/tsukena/backup/` にその日のバックアップ（`tsukena-YYYY-MM-DD.db`）ができている

## 更新するとき

```sh
cd /opt/tsukena
sudo -u tsukena git pull
sudo -u tsukena /home/tsukena/.local/bin/uv sync --frozen
sudo systemctl restart tsukena-api tsukena-bot
```

アプリを変えたときは、手順4のビルドと配置をし直す（API の再起動は要らない）。
systemd のファイルを変えたときは、手順5のコピーと `daemon-reload` をし直す。

## うまく動かないとき

| 症状 | 見るところ |
| --- | --- |
| bot が返事をしない | `journalctl -u tsukena-bot`。`KeyError` なら `.env` の変数が足りない |
| bot が「記録できませんでした」と返す | `journalctl -u tsukena-api` と `tsukena-bot`。`401` なら `.env` の `TSUKENA_BOT_API_TOKEN` が API と bot で食い違っている |
| アプリの一覧が出ない | ブラウザの開発者ツールの Network。`401` ならビルドに入れたトークンが `.env` と違う。Access のログイン画面への移動が出ていれば、ページを読み込み直してログインし直す |
| `https://tsukena.example.com` が開かない | `systemctl status cloudflared` と、Cloudflare のダッシュボードのトンネルの状態 |
| アプリが古いまま | ブラウザのキャッシュ（Flutter の service worker）。読み込み直すか、サイトのデータを消す |

## まだ決まっていないこと

- **バックアップの外への退避（R-2）**: 今は同じ機械の中に30日分を残すだけで、機械が壊れると失われる。
