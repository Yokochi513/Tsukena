# ADR-0010: Web 版のアプリは GitHub Pages に置き、トークンはアプリの画面で入力する

- 状態: 採用
- 日付: 2026-10-20

## 背景

[ADR-0009](./0009-web-app-via-cloudflare-tunnel.md) では、Web 版のアプリを API のプロセスから同じオリジンで配信し、Cloudflare Access のログインの後ろに置くと決めた。
その後、コードを GitHub の非公開リポジトリにも置き、Web 版は GitHub Pages で配信することにした。サーバーにビルド結果を手で送る手間をなくし、push するだけで配置されるようにするためである。

GitHub Pages には、次の性質がある。

- 配信されるサイトは、リポジトリが非公開でも誰でも読める。閲覧者を絞れるのは Enterprise Cloud だけである。
- 非公開のリポジトリで Pages を使うには、GitHub の有料プラン（Pro 以上）が要る。
- サイトのオリジン（`https://yokochi513.github.io`）は、API のオリジンと別になる。

これまでのビルドは、アプリ用のトークンを `main.dart.js` に埋め込んでいた。このまま Pages に置くと、トークンがインターネットに公開される。

## 選択肢

1. これまでのビルドのまま Pages に置く
2. トークンをビルドに入れず、アプリの画面で入力してブラウザに保存する
3. Pages を使わず、ADR-0009 のまま API から配信する

## 決定

2 を採用する。

- **トークンはビルドに入れない。** 初めて開いたときにトークンの入力画面を出し、入力された値を API で一度確かめてから、ブラウザに保存する（`shared_preferences`、Web では localStorage）。
  API が 401 を返したら、保存したトークンを消して入力画面に戻す（`app/lib/core/api_http.dart`）。
- ビルドに入れるのは API の URL（`API_BASE_URL`）だけとする。秘密ではないので、公開されてよい。値は GitHub のリポジトリの変数に置く。
- **GitHub Actions で、`master` に `app/` の変更を push するたびにビルドして Pages に置く**（`.github/workflows/pages.yml`）。
- API は Pages のオリジンからの呼び出しを CORS で許可する（`tsukena/config.toml` の `[cors]`）。
- **API の前の Cloudflare Access はやめ、API はトークンだけで守る。** 別オリジンから `fetch` で呼ぶ API の前に Access を置くと、プリフライト（OPTIONS）が Access のログインに止められ、ブラウザから呼べなくなるためである。
  トークンは 32 バイトの乱数で、推測されることはない。漏れたときは作り直せば、それまでの値は使えなくなる。
- API のプロセスから Web 版を配信する仕組み（ADR-0009）は外す。
- Cloudflare Tunnel で API を外に出すこと、API が `127.0.0.1` で待ち受けることは、ADR-0009 のまま変えない。

## 結果

- `master` に push するだけで、Web 版が新しくなる。サーバーにビルド結果を送る手順が要らない。
- 公開される `main.dart.js` に秘密が入らない。
- 端末（ブラウザ）ごとに、最初の一度だけトークンを入力する必要がある。トークンを作り直したときは、各端末で入れ直す（401 で入力画面に戻る）。
- トークンはブラウザの localStorage に平文で残る。同じブラウザで動く別のスクリプト（XSS）からは読める。Pages のサイトには自分のアプリしか置かないので、許容する。
- API は、トークンさえ知っていれば誰でも呼べる。Cloudflare Access による二重の守りは失われる。
- Pages を使うため、GitHub の有料プラン（Pro 以上）が要る。
- 次の文書とファイルを本 ADR に合わせて直す。
  - [ADR-0009](./0009-web-app-via-cloudflare-tunnel.md) の状態（一部を本 ADR で置き換え）
  - [design.md](../design.md) 11章（外部への公開）、12章、13章（R-1・R-5）
  - [deploy.md](../deploy.md) の Web 版のビルドと配置、Cloudflare Access の手順
