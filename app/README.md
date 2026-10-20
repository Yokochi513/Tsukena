# Tsukena スマホアプリ

## アプリアイコン

A案（財布とコイン）の元画像は `assets/icon/tsukena-icon.png`。
Android・iOS・Web用アイコンは、`app/` で次のコマンドを実行して再生成する。

```sh
flutter pub get
dart run flutter_launcher_icons
```

Discord用には `../output/tsukena-discord-icon.png` を使用する。

Flutter（Dart）で開発する、記録修正・確認待ちの分類・振り返り用のアプリ。
サーバーの REST API を呼び出す構成とする（[基本設計](../docs/design.md)）。

現在は Flutter 標準のカウンター画面とテストを含む初期ひな形で、家計簿の画面や API 通信は未実装。
Android・iOS のひな形を生成済み。正式な対象 OS と配布方法は未決定。

`app/` で次のコマンドを実行する。

```sh
flutter pub get
flutter run
```

検証:

```sh
flutter analyze
flutter test
```

iOS のビルドには macOS と Xcode が必要。
