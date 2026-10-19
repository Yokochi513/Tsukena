# ADR-0009: アプリは Web 版を API から配信し、Cloudflare Tunnel と Cloudflare Access で外に出す

- 状態: 採用
- 日付: 2026-10-20

## 背景

API と bot を自宅の Linux サーバーで常駐させて、使い始めることにした。
そのためには、次の2つの残課題を決める必要があった。

- R-1: スマホアプリから API に届く経路。外出先から使えることが条件である。
- R-5: Flutter アプリの対象 OS と配布方法。

アプリが API を呼ぶには、アプリ用のトークンをアプリに持たせる必要がある（→ [ADR-0007](./0007-bot-accesses-data-through-api.md)）。
トークンはビルドするときに埋め込むので、アプリのファイルを手に入れた人は誰でも取り出せる。

## 選択肢

R-1（経路）

1. Tailscale などの VPN で、自分の端末からだけ届くようにする
2. Cloudflare Tunnel で、インターネットに HTTPS で公開する
3. VPS で直接 HTTPS を公開する

R-5（対象と配布）

1. Android の APK を端末に直接入れる
2. iPhone に Xcode から入れる
3. Web 版をサーバーから配信し、ブラウザで使う

## 決定

R-1 は 2、R-5 は 3 を採用する。

- **Web 版のアプリは、API のプロセスが API と同じオリジンで配信する。**
  `flutter build web` の結果（`app/build/web`）があれば、API のパスに当たらないリクエストに静的ファイルとして返す（`tsukena.config.load_web_dir()`）。
  同じオリジンなので、本番では CORS の設定が要らない。
- **外からは Cloudflare Tunnel を通してだけ届かせる。** API は `127.0.0.1` で待ち受け、自宅のルーターのポートは開けない。
  bot は同じ機械の中から API を呼ぶので、Tunnel を通らない。
- **Tunnel の前に Cloudflare Access を置き、自分のアカウントでログインしないと何も見えないようにする。**
  Web 版では、アプリ用のトークンが配信する JavaScript（`main.dart.js`）に入る。
  Access が無いと、URL を知った人は誰でもトークンを取り出し、API を呼べてしまう。
  Access を置くことで、守りが「トークンを知っているか」だけでなく「自分のアカウントでログインしたか」の二重になる。
- Flutter で作ること（[ADR-0003](./0003-native-mobile-app.md)）は変えない。端末に入れるネイティブアプリにするかは、Web 版を使ってみてから決め直す。

## 結果

- スマホにも PC にも、アプリを入れずにブラウザで使える。ビルドと配布は、サーバーに `app/build/web` を置き直すだけになる。
- 外出先からも、スマホの設定（VPN のアプリなど）なしで使える。
- Cloudflare のアカウントと、Cloudflare で管理するドメインが必要になる。
- Cloudflare Access のログインが切れると、アプリの API の呼び出しが失敗する。そのときはページを読み込み直してログインし直す。
- Cloudflare Access を設定し忘れると、アプリ用のトークンが公開される。手順は [deploy.md](../deploy.md) に、公開より先に行う手順として書く。
- 今後 Gmail の連携（`/oauth/google/callback`）を作るときは、Google からのリダイレクトがブラウザ経由で届くので、Access のログイン済みのブラウザで行えば通る。Access の対象から外す必要があるかは、そのときに確かめる。
- 次の文書を本 ADR に合わせて直す。
  - [design.md](../design.md) 11章（外部への公開）、12章（アプリのひな形）、13章（R-1・R-5）
  - [README](../../README.md) の未決定（対象 OS と配布方法）
