# サーバーへの置き方

自宅の Linux サーバー（Raspberry Pi など）で API と bot を常駐させ、API を Cloudflare Tunnel で外に出す手順。
Web 版のアプリは GitHub Pages に置く。
構成の理由は [ADR-0009](./adr/0009-web-app-via-cloudflare-tunnel.md) と [ADR-0010](./adr/0010-web-app-on-github-pages.md) にある。

```
スマホ・PC のブラウザ
   │  ① アプリを読み込む            ② API を呼ぶ（Authorization: Bearer ...）
   ▼                                 ▼
GitHub Pages                     Cloudflare Tunnel ──（サーバーからの外向きの接続。ルーターのポートは開けない）
https://yokochi513.github.io/Tsukena/   │
                                     ▼  サーバーの中
                                  cloudflared ─▶ 127.0.0.1:8000  tsukena-api
                                                      ▲
                                                      │ 同じ機械の中で呼ぶ
                                                 tsukena-bot ─▶ Discord
```

## 0. 用意するもの

| もの | 内容 |
| --- | --- |
| Linux のサーバー | 64 ビットの Raspberry Pi OS（Bookworm 以降）や Ubuntu など。Python 3.11 以上が入っていること（`python3 --version`） |
| Cloudflare のアカウント | 無料のプランでよい |
| ドメイン | Cloudflare で DNS を管理しているもの。以下では API のホスト名を `tsukena.example.com` と書く |
| GitHub | 非公開のリポジトリで Pages を使うため、有料プラン（Pro 以上）が要る |
| Discord の bot | Developer Portal で作った bot のトークン。自分しかいないサーバーに招待しておく（README「初期設定」） |

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

リポジトリは非公開なので、clone のときに認証が要る。サーバーには、読み取りだけの権限のトークン（GitHub の fine-grained personal access token の Contents: Read-only、または deploy key）を使う。

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
API はトークンだけで守られている（→ [ADR-0010](./adr/0010-web-app-on-github-pages.md)）ので、トークンはどこにも貼らない。

## 3. DB を作る

```sh
sudo -u tsukena .venv/bin/python -m tsukena.init_db
```

テーブルと、カテゴリ・設定の初期値（README「カテゴリ（初期値）」、月の予算 80,000円）だけが入る。
DB が既にあるときは上書きせずに止まる。

開発中の `db/tsukena.db` をそのまま持っていくこともできるが、`sql/sample/` のサンプルの支出・収入が入っているので勧めない。

## 4. API と bot を常駐させる

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
```

Discord で bot に `テスト 1` と送り、返事が来れば bot から API までつながっている。確かめた記録は、後でアプリから消す。

## 5. Cloudflare Tunnel で API を外に出す

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

このホスト名には、Cloudflare Access を**設定しない**。ブラウザから別のオリジンの API を呼ぶときのプリフライトが、Access に止められるためである（→ [ADR-0010](./adr/0010-web-app-on-github-pages.md)）。

## 6. Web 版のアプリを GitHub Pages に置く

手元の PC か GitHub の画面で行う。

1. リポジトリの **Settings → Pages** で、Source を **GitHub Actions** にする。
2. **Settings → Secrets and variables → Actions → Variables** に、変数 `API_BASE_URL` を `https://tsukena.example.com` で作る。
   トークンは**ここに置かない**。ビルドに入ると、Pages で公開されるためである。
3. **Actions → Deploy web app to Pages → Run workflow** で一度動かす。以降は `master` に `app/` の変更を push するたびに動く。

API の側では、Pages のオリジンを `tsukena/config.toml` の `[cors]` に書いておく（`https://yokochi513.github.io`）。リポジトリの持ち主が変わったときは、ここも変える。

## 7. 外から確かめる

スマホのモバイル回線（Wi-Fi を切った状態）で、次を確かめる。

- [ ] `https://yokochi513.github.io/Tsukena/` を開くと、トークンの入力画面が出る
- [ ] 違う値を入れると「トークンが違います」と出て、保存されない
- [ ] 手順2の `TSUKENA_APP_API_TOKEN` を入れると、支出・収入の一覧が読める
- [ ] ページを読み込み直しても、トークンを入れ直さずに一覧が出る
- [ ] Discord で記録すると、アプリの一覧に出る
- [ ] 翌日、`/opt/tsukena/backup/` にその日のバックアップ（`tsukena-YYYY-MM-DD.db`）ができている

## 更新するとき

サーバーのコード（API・bot）を変えたとき:

```sh
cd /opt/tsukena
sudo -u tsukena git pull
sudo -u tsukena /home/tsukena/.local/bin/uv sync --frozen
sudo systemctl restart tsukena-api tsukena-bot
```

systemd のファイルを変えたときは、手順4のコピーと `daemon-reload` をし直す。
アプリ（`app/`）を変えたときは、`master` に push すれば GitHub Actions が Pages に置き直す。

トークンを作り直したとき:

1. サーバーの `.env` を書き換え、`sudo systemctl restart tsukena-api tsukena-bot` で再起動する。
2. 各端末でアプリを開くと 401 で入力画面に戻るので、新しいトークンを入れる。

## うまく動かないとき

| 症状 | 見るところ |
| --- | --- |
| bot が返事をしない | `journalctl -u tsukena-bot`。`KeyError` なら `.env` の変数が足りない |
| bot が「記録できませんでした」と返す | `journalctl -u tsukena-api` と `tsukena-bot`。`401` なら `.env` の `TSUKENA_BOT_API_TOKEN` が API と bot で食い違っている |
| アプリが「API に接続できませんでした」と出す | ブラウザの開発者ツールの Console。CORS のエラーなら `tsukena/config.toml` の `[cors]` に Pages のオリジンが無い。接続できないなら `systemctl status cloudflared` |
| アプリが開いてすぐ止まる（画面が真っ白） | GitHub の変数 `API_BASE_URL` が空のままビルドされた。Actions のログを見る |
| `https://tsukena.example.com` に届かない | `systemctl status cloudflared` と、Cloudflare のダッシュボードのトンネルの状態 |
| アプリが古いまま | ブラウザのキャッシュ（Flutter の service worker）。読み込み直すか、サイトのデータを消す（保存したトークンも消えるので入れ直す） |

## まだ決まっていないこと

- **バックアップの外への退避（R-2）**: 今は同じ機械の中に30日分を残すだけで、機械が壊れると失われる。
