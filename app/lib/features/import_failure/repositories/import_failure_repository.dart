import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/import_failure/entities/import_failure.dart';

class ImportFailureService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  ImportFailureService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  /// 取り込めなかったメールを、失敗した日時の新しい順に返す。
  Future<List<ImportFailure>> getImportFailures() async {
    final response = await ApiHttp.get(Uri.parse('$baseUrl/import-failures'));

    if (response.statusCode != 200) {
      throw Exception('取り込めなかったメールの取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => ImportFailure.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 取り込めなかったメールを、その場で取り込み直す。記録した支払いの件数を返す。
  ///
  /// まだ解析できないときは [ImportRetryFailedException] を投げる（理由を持つ）。
  Future<int> retryImport(String messageId) async {
    final response = await ApiHttp.post(
      Uri.parse(
        '$baseUrl/import-failures/${Uri.encodeComponent(messageId)}/retry',
      ),
    );

    switch (response.statusCode) {
      case 200:
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json['recorded'] as int;
      case 422:
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        throw ImportRetryFailedException(json['detail'] as String);
      case 404:
        // 別の端末で取り込み直し済み
        throw ImportRetryFailedException('既に取り込み直されています');
      case 503:
        throw ImportRetryFailedException('Gmail と連携していません');
      default:
        throw Exception('取り込み直しに失敗しました');
    }
  }
}

/// 取り込み直したが、記録できなかった。[reason] はそのまま画面に出す。
class ImportRetryFailedException implements Exception {
  ImportRetryFailedException(this.reason);

  final String reason;
}
