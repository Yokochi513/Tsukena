import 'dart:js_interop';

import 'package:web/web.dart' as web;

/// 文字列をファイルにして、ブラウザでダウンロードさせる
Future<void> saveTextFile(
  String fileName,
  String content,
  String mimeType,
) async {
  final blob = web.Blob(
    [content.toJS].toJS,
    web.BlobPropertyBag(type: mimeType),
  );
  final url = web.URL.createObjectURL(blob);
  final anchor = web.HTMLAnchorElement()
    ..href = url
    ..download = fileName;
  web.document.body!.append(anchor);
  anchor.click();
  anchor.remove();
  web.URL.revokeObjectURL(url);
}
