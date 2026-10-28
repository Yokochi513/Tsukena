// 端末にファイルを保存する。Web 版ではブラウザのダウンロードにする。
// アプリは Web 版で使う（→ docs/adr/0010）。ほかの環境ではまだ保存できない
export 'save_file_stub.dart' if (dart.library.js_interop) 'save_file_web.dart';
